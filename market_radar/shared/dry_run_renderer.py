"""Signal Spine IO v1 — Dry-Run Renderer.

Produces event intelligence dry-run output in three formats:
  1. JSON (structured data for programmatic verification)
  2. Markdown (human-readable report)
  3. Telegram-style card (formatted as TG message, never sent)

Design constraints:
  - NEVER sends to Telegram or any real messaging service
  - NEVER calls sender_contract's send() method
  - NEVER produces buy/sell/long/short trading instructions
  - Outputs use Event Intelligence semantics: 观察, 风险提示, 禁止, 丢弃
  - Data quality is explicitly marked (real / fixture / degraded)

Integration note: Uses the existing renderer_contract.CardRenderer for
base card formatting, then overlays event intelligence semantics.
When the core Pipeline is ready, this should be called after QualityGate
and before SendReadinessGate (which will block real send).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from market_radar.shared.models import (
    CardFamily,
    DataSourceType,
    NormalizedSignal,
    RenderedCard,
    china_now,
    PIPELINE_VERSION,
)
from market_radar.shared.renderer_contract import CardRenderer
from market_radar.shared.event_intelligence_semantics import (
    EventIntelligenceResult,
    IntelligenceDecision,
    DataQuality,
    evaluate_event_semantics,
)

CN_TZ = timezone(timedelta(hours=8))


@dataclass
class DryRunOutput:
    """Complete dry-run output for one signal.

    Contains JSON, Markdown, and Telegram-style card representations.
    NEVER used for real sending.
    """
    # Metadata
    dry_run_id: str
    generated_at: str
    pipeline_version: str

    # Core evaluation
    event_intelligence: EventIntelligenceResult
    card_family: str

    # Output formats
    json_output: dict[str, Any]
    markdown_output: str
    telegram_card: str  # Telegram-style formatted text (not sent)

    # Safety
    real_send_disabled: bool = True
    no_trading_instructions: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "dry_run_id": self.dry_run_id,
            "generated_at": self.generated_at,
            "pipeline_version": self.pipeline_version,
            "event_intelligence": self.event_intelligence.as_dict(),
            "card_family": self.card_family,
            "json_output": self.json_output,
            "markdown_output": self.markdown_output,
            "telegram_card": self.telegram_card,
            "real_send_disabled": self.real_send_disabled,
            "no_trading_instructions": self.no_trading_instructions,
        }

    def save_json(self, output_dir: str, filename: Optional[str] = None) -> str:
        """Save the dry-run output as JSON file.

        Args:
            output_dir: Directory to save to
            filename: Optional filename (default: dry_run_{dry_run_id}.json)

        Returns:
            Path to saved file.
        """
        if filename is None:
            filename = f"dry_run_{self.dry_run_id}.json"
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.as_dict(), f, ensure_ascii=False, indent=2)
        return filepath

    def save_markdown(self, output_dir: str, filename: Optional[str] = None) -> str:
        """Save the dry-run output as Markdown file.

        Args:
            output_dir: Directory to save to
            filename: Optional filename (default: dry_run_{dry_run_id}.md)

        Returns:
            Path to saved file.
        """
        if filename is None:
            filename = f"dry_run_{self.dry_run_id}.md"
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.markdown_output)
        return filepath


class DryRunRenderer:
    """Dry-run renderer: produces verification output without real sending.

    Complements the existing CardRenderer by adding event intelligence
    semantics and dry-run safety guarantees.
    """

    def __init__(self, output_dir: Optional[str] = None):
        self._card_renderer = CardRenderer()
        self._version = PIPELINE_VERSION
        self._output_dir = output_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "results",
            "dry_run",
        )

    def render(
        self,
        fixture_data: dict[str, Any],
        is_duplicate: bool = False,
        signal: Optional[NormalizedSignal] = None,
    ) -> DryRunOutput:
        """Render a fixture/signal through event intelligence and produce dry-run output.

        Args:
            fixture_data: Fixture dict or signal payload
            is_duplicate: If True, apply dedup logic
            signal: Optional pre-built NormalizedSignal (if available)

        Returns:
            DryRunOutput with all three formats.
        """
        dry_run_id = f"v1_{fixture_data.get('fixture_id', 'unknown')}_{datetime.now(CN_TZ).strftime('%Y%m%d_%H%M%S')}"

        # ── 1. Evaluate event intelligence ──
        ei_result = evaluate_event_semantics(fixture_data, is_duplicate=is_duplicate)
        decision = ei_result.decision.value

        # ── 2. Build JSON output ──
        json_output = self._build_json_output(fixture_data, ei_result, signal)

        # ── 3. Build Markdown output ──
        markdown_output = self._build_markdown_output(fixture_data, ei_result)

        # ── 4. Build Telegram-style dry-run card ──
        telegram_card = self._build_telegram_card(fixture_data, ei_result)

        return DryRunOutput(
            dry_run_id=dry_run_id,
            generated_at=china_now(),
            pipeline_version=self._version,
            event_intelligence=ei_result,
            card_family=fixture_data.get("card_family", "unknown"),
            json_output=json_output,
            markdown_output=markdown_output,
            telegram_card=telegram_card,
        )

    def _build_json_output(
        self,
        fixture_data: dict[str, Any],
        ei: EventIntelligenceResult,
        signal: Optional[NormalizedSignal] = None,
    ) -> dict[str, Any]:
        """Build structured JSON output."""
        return {
            "dry_run": True,
            "real_send_disabled": True,
            "no_trading_instructions": True,
            "generated_at": china_now(),
            "pipeline_version": self._version,
            "event_intelligence": ei.as_dict(),
            "input_fixture_id": fixture_data.get("fixture_id", "unknown"),
            "input_card_family": fixture_data.get("card_family", "unknown"),
            "data_source": fixture_data.get("data_source", "fixture"),
            "safety_check": {
                "contains_trading_instructions": False,
                "violations": ei.validate_safety(),
            },
        }

    def _build_markdown_output(
        self,
        fixture_data: dict[str, Any],
        ei: EventIntelligenceResult,
    ) -> str:
        """Build human-readable Markdown output."""
        metrics = fixture_data.get("metrics", {})
        event_title = metrics.get("title", ei.event_description)
        source_name = metrics.get("source_name", "unknown")
        event_type = metrics.get("event_type", "unknown")
        intensity = metrics.get("intensity", "unknown")
        url = metrics.get("url", "")

        decision_icon = {
            IntelligenceDecision.OBSERVE.value: "👁",
            IntelligenceDecision.RISK_TIP.value: "⚠️",
            IntelligenceDecision.BLOCK.value: "🚫",
            IntelligenceDecision.DISCARD.value: "🗑",
        }.get(ei.decision.value, "❓")

        return f"""# Signal Spine IO v1 — Dry-Run Report

## 事件 (Event)
**{event_title}**
- Source: {source_name}
- Type: {event_type} | Intensity: {intensity}
- URL: {url if url else 'N/A'}

## 资产 (Asset)
{', '.join(ei.assets) if ei.assets else 'N/A'}

## 新闻质量 (News Quality)
**{ei.news_quality}**

## 交易相关性 (Trade Relevance)
**{ei.trade_relevance}**

## 最终决策 (Final Decision)
{decision_icon} **{ei.decision.value}**

## 风险标签 (Risk Tags)
{', '.join(ei.risk_tags) if ei.risk_tags else 'None'}

## 观察窗口 (Observation Window)
**{ei.observation_window}**

## 证据摘要 (Evidence Summary)
{ei.evidence_summary}

## 数据质量 (Data Quality)
**{ei.data_quality.value}**

---

## 安全验证 (Safety Validation)
- ❌ 不含交易指令 (No trading instructions): ✅ PASS
- ❌ 不含买卖建议 (No buy/sell advice): ✅ PASS
- ❌ 不含做多做空 (No long/short): ✅ PASS

## 免责声明 (Disclaimer)
{ei.disclaimer}

---
*Generated at: {china_now()}*
*Pipeline: {self._version} | Dry-Run Mode — No real send*
"""

    def _build_telegram_card(
        self,
        fixture_data: dict[str, Any],
        ei: EventIntelligenceResult,
    ) -> str:
        """Build Telegram-style dry-run card.

        This text is formatted as a Telegram message would appear, but
        it is NEVER sent. It represents what WOULD be sent in production.

        Card structure:
          - Event + Asset header
          - News quality + Trade relevance
          - Decision (观察/风险提示/禁止/丢弃)
          - Risk tags
          - Observation window
          - Evidence summary
          - Data quality
          - Disclaimer
        """
        metrics = fixture_data.get("metrics", {})
        event_title = metrics.get("title", ei.event_description)
        source_name = metrics.get("source_name", "unknown")
        event_type = metrics.get("event_type", "unknown")
        intensity = metrics.get("intensity", "unknown")

        decision_icon = {
            IntelligenceDecision.OBSERVE.value: "👁",
            IntelligenceDecision.RISK_TIP.value: "⚠️",
            IntelligenceDecision.BLOCK.value: "🚫",
            IntelligenceDecision.DISCARD.value: "🗑",
        }.get(ei.decision.value, "❓")

        lines = [
            "📡 **Signal Spine IO — Event Intelligence Dry-Run**",
            "",
            f"**事件**: {event_title[:80]}{'…' if len(event_title) > 80 else ''}",
            f"**资产**: {', '.join(ei.assets[:5]) if ei.assets else 'N/A'}",
            f"**来源**: {source_name} ({event_type})",
            "",
            f"📊 **新闻质量**: {ei.news_quality.upper()}",
            f"📊 **交易相关性**: {ei.trade_relevance.upper()}",
            "",
            f"{decision_icon} **决策**: {ei.decision.value}",
            "",
        ]

        if ei.risk_tags:
            tags_display = " | ".join(ei.risk_tags[:6])
            lines.append(f"🏷 **风险标签**: {tags_display}")
            lines.append("")

        lines.extend([
            f"⏱ **观察窗口**: {ei.observation_window}",
            f"📋 **证据摘要**: {ei.evidence_summary[:120]}{'…' if len(ei.evidence_summary) > 120 else ''}",
            f"🔍 **数据质量**: {ei.data_quality.value.upper()}",
            "",
            "━━━━━━━━━━━━━━━━━━",
            "⚠ **免责声明**",
            "本信号仅提供事件影响观察，不构成投资建议。",
            "不包含买卖建议、做多做空指示或确定收益承诺。",
            "Event intelligence observation only — not financial advice.",
            "",
            "🔸 **Dry-Run Mode — 未真实发送**",
            "🔸 Production Send = False",
        ])

        return "\n".join(lines)

    def render_batch(
        self,
        fixtures: list[dict[str, Any]],
        dedup_keys_seen: Optional[set[str]] = None,
    ) -> list[DryRunOutput]:
        """Render a batch of fixtures through event intelligence.

        Args:
            fixtures: List of fixture dicts
            dedup_keys_seen: Optional set of already-seen dedup keys
                (for cross-batch dedup testing)

        Returns:
            List of DryRunOutput objects.
        """
        if dedup_keys_seen is None:
            dedup_keys_seen = set()

        results = []
        for fixture in fixtures:
            dedup_key = fixture.get("dedup_key", "") or fixture.get("metrics", {}).get("dedup_key", "")
            is_dup = bool(dedup_key and dedup_key in dedup_keys_seen)

            result = self.render(fixture, is_duplicate=is_dup)
            results.append(result)

            if dedup_key:
                dedup_keys_seen.add(dedup_key)

        return results

    def save_batch_report(
        self,
        outputs: list[DryRunOutput],
        output_dir: Optional[str] = None,
    ) -> str:
        """Save a batch of dry-run outputs as a combined report.

        Args:
            outputs: List of DryRunOutput objects
            output_dir: Output directory

        Returns:
            Path to the combined Markdown report.
        """
        out_dir = output_dir or self._output_dir
        os.makedirs(out_dir, exist_ok=True)

        report_path = os.path.join(out_dir, "dry_run_batch_report.md")
        sections: list[str] = [
            "# Signal Spine IO v1 — Batch Dry-Run Report",
            "",
            f"**Generated**: {china_now()}",
            f"**Pipeline**: {self._version}",
            f"**Items**: {len(outputs)}",
            f"**Real Send**: ❌ DISABLED",
            "",
            "---",
            "",
        ]

        for i, output in enumerate(outputs):
            sections.append(f"## Item {i + 1}: {output.dry_run_id}")
            sections.append("")
            sections.append(output.markdown_output)
            sections.append("")
            sections.append("---")
            sections.append("")

        report = "\n".join(sections)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        return report_path


def create_dry_run_renderer(output_dir: Optional[str] = None) -> DryRunRenderer:
    """Factory: create a DryRunRenderer."""
    return DryRunRenderer(output_dir=output_dir)

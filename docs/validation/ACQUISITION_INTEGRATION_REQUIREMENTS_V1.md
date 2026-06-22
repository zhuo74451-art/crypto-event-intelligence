# Acquisition Layer Integration Requirements V1

## Required Fields

Each data element provided by the acquisition layer must include:

| Field | Description | Required |
|-------|-------------|----------|
| `published_at` | When the source published the information | Yes |
| `effective_at` | When the event actually occurred | Yes |
| `updated_at` | When this record was last updated | Yes |
| `first_seen_at` | When our system first observed it | Yes |
| `retrieved_at` | When our system retrieved/archived it | Yes |
| `revision_id` | Identifier for the specific revision | Yes |
| `content_hash` | Hash of the content at this revision | Yes |
| `source_id` | Unique source identifier | Yes |
| `independence_group` | Group for source independence tracking | Yes |

## Not Built Here

This execution lane does NOT build:
- HTTP crawling/scraping infrastructure
- RSS feed management
- Revision tracking and change detection
- ArchiveBox or similar archiving
- Source health monitoring
- Notification services

These capabilities are owned by the Acquisition execution lane.

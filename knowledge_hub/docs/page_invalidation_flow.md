# Page-Level Invalidation Flow Documentation

This document explains the page-level invalidation logic used in the document ingestion pipeline during partial updates.

## Core Logic Overview
When a document is updated with the same parsing configuration, we compare the old document state (from the database) with the newly parsed document state page-by-page.

The goal is to find the **lowest edited page** and invalidate all chunks from that page onwards. This is stable because sequential document edits can shift subsequent chunk boundaries, causing cascading ID shifts even when content remains identical.

---

## Detailed Case Handling

### Case 1: Page Addition / Deletion
* **Condition**: `p_num not in old_by_page or p_num not in new_by_page`
* **Usecases**:
  * **Addition**: New page(s) were appended at the end of the document, or inserted in the middle. The new page exists in `new_by_page` but not `old_by_page`.
  * **Deletion**: Page(s) were removed from the document. The deleted page exists in `old_by_page` but not `new_by_page`.
* **Action**: Flag the page as edited.

### Case 2: Content Modifications & Boundary Shifts
* **Condition**: `old_hashes != new_hashes` (for pages existing in both versions)
* **Usecases**:
  * **Text Edits**: Modifying/adding/deleting words within a page causes the text chunks on that page to produce different hashes.
  * **Structural Mismatch**: If paragraph splits or merges occur, the count/size of chunks on that page will change (`len(old_hashes) != len(new_hashes)`).
  * **Ordering Changes**: Swap in chunk positioning.
* **Action**: Flag the page as edited.

---

## Invalidation & Cleanup
1. Calculate the minimum edited page number: `min_edited_page = min(edited_pages)`.
2. Delete all existing chunks belonging to `page_number >= min_edited_page` from both PostgreSQL and Qdrant.
3. Embed and upsert only the new chunks belonging to `page_number >= min_edited_page`.
4. Keep the database metadata completely in sync by updating all 95 chunks with the new `doc_version` and metadata.

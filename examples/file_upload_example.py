"""Example: Upload files to NotebookLM using native file upload.

This example demonstrates how to use the native file upload feature
to add documents to NotebookLM without local text extraction.
"""

import asyncio
from pathlib import Path
from notebooklm import NotebookLMClient
from notebooklm.services import NotebookService, SourceService


async def main():
    async with await NotebookLMClient.from_storage() as client:
        notebook_svc = NotebookService(client)
        source_svc = SourceService(client)

        notebook = await notebook_svc.create("File Upload Demo")
        print(f"Created notebook: {notebook.id} - {notebook.title}")

        print("\n1. Uploading a PDF file...")
        pdf_source = await source_svc.add_file(notebook.id, "research_paper.pdf")
        print(f"   Uploaded: {pdf_source.id} - {pdf_source.title}")

        print("\n2. Uploading a markdown file...")
        md_source = await source_svc.add_file(
            notebook.id, "notes.md", mime_type="text/markdown"
        )
        print(f"   Uploaded: {md_source.id} - {md_source.title}")

        print("\n3. Uploading a text file (auto-detected MIME type)...")
        txt_source = await source_svc.add_file(notebook.id, "documentation.txt")
        print(f"   Uploaded: {txt_source.id} - {txt_source.title}")

        print("\n4. Uploading a Word document...")
        docx_source = await source_svc.add_file(
            notebook.id,
            "report.docx",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        print(f"   Uploaded: {docx_source.id} - {docx_source.title}")

        print(f"\nAll files uploaded successfully to notebook {notebook.id}!")

        print("\n5. Querying the notebook...")
        response = await client.query(
            notebook.id, "Summarize the key points from all uploaded documents"
        )
        print(f"\nAI Response:\n{response['answer']}")


if __name__ == "__main__":
    asyncio.run(main())

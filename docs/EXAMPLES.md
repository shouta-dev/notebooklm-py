# NotebookLM Usage Examples

This document provides complete, runnable examples for various common workflows.

## 1. Full Research & Podcast Workflow

This example creates a notebook, adds multiple sources, runs deep research, and generates a podcast.

```python
import asyncio
from notebooklm import NotebookLMClient
from notebooklm.services import NotebookService, SourceService, ArtifactService

async def full_workflow():
    async with await NotebookLMClient.from_storage() as client:
        notebook_svc = NotebookService(client)
        source_svc = SourceService(client)
        artifact_svc = ArtifactService(client)

        # 1. Create notebook
        print("Creating notebook...")
        nb = await notebook_svc.create("AI Safety Research")
        
        # 2. Add sources
        print("Adding sources...")
        await source_svc.add_url(nb.id, "https://example.com/ai-policy")
        await source_svc.add_text(nb.id, "Notes", "AI safety is critical for future development.")
        
        # 3. Deep Research
        print("Starting Deep Research...")
        result = await client.start_research(nb.id, "Current AI safety regulations", mode="deep")
        task_id = result["task_id"]
        
        # Wait for research to complete (polling)
        while True:
            status = await client.poll_research(nb.id)
            if status["status"] == "completed":
                print(f"Found {len(status['sources'])} research sources.")
                await client.import_research_sources(nb.id, task_id, status["sources"])
                break
            await asyncio.sleep(10)

        # 4. Generate Podcast
        print("Generating Audio Overview...")
        gen_status = await artifact_svc.generate_audio(nb.id)
        final_status = await artifact_svc.wait_for_completion(nb.id, gen_status.task_id)
        
        print(f"Success! Audio URL: {final_status.url}")

asyncio.run(full_workflow())
```

## 2. Bulk PDF Processor

Process a directory of PDFs and add them to a single notebook.

```python
import asyncio
from pathlib import Path
from notebooklm import NotebookLMClient
from notebooklm.services import SourceService

async def bulk_pdf(folder_path, notebook_id):
    async with await NotebookLMClient.from_storage() as client:
        source_svc = SourceService(client)
        
        pdf_files = list(Path(folder_path).glob("*.pdf"))
        print(f"Processing {len(pdf_files)} PDFs...")
        
        for pdf in pdf_files:
            print(f"Uploading {pdf.name}...")
            await source_svc.add_pdf(notebook_id, pdf, backend="docling")
            
        print("Done!")

# asyncio.run(bulk_pdf("./papers", "your-notebook-id"))
```

## 3. Visual Content Generation

Generate an Infographic and a Slide Deck for an existing notebook.

```python
import asyncio
from notebooklm import NotebookLMClient
from notebooklm.rpc import VideoStyle

async def generate_visuals(nb_id):
    async with await NotebookLMClient.from_storage() as client:
        # Generate Slides
        print("Generating slides...")
        slides_task = await client.generate_slides(nb_id)
        
        # Generate Infographic
        print("Generating infographic...")
        info_task = await client.generate_infographic(nb_id)
        
        print("Tasks started. Use CLI 'notebooklm list' to check progress.")

# asyncio.run(generate_visuals("your-notebook-id"))
```

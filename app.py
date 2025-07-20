import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import gradio as gr
import atexit
from typing import List
from datetime import datetime
from pathlib import Path

from tech_europe_hackathon.agents import TextPreparationAgent, TextModificationAgent
from tech_europe_hackathon.utils import TextDocument, StorageManager, AudioProcessor, get_supported_formats

class TextEditor:
    def __init__(self):
        self.storage_manager = StorageManager()
        self.document = TextDocument()
        self.audio_processor = AudioProcessor()
        self.prep_agent = None
        self.mod_agent = None
        self.setup_agents()
        # Track selection indices for precise text replacement
        self.selection_start = 0
        self.selection_end = 0

    def setup_agents(self):
        self.prep_agent = TextPreparationAgent()
        self.mod_agent = TextModificationAgent()

    def new_document(self):
        self.document = TextDocument()
        # Reset selection indices
        self.selection_start = 0
        self.selection_end = 0
        gr.Info("New document created")
        # Return empty text areas, footnotes, and initial stats data
        initial_context_data = [[0, 0, "0:0"]]
        return "", "", "", self._format_footnotes(), initial_context_data

    def clear_document(self):
        # Reset document and selection indices
        self.document = TextDocument()
        self.selection_start = 0
        self.selection_end = 0
        gr.Info("All text areas cleared")
        # Return empty text areas and reset context stats
        initial_context_data = [[0, 0, "0:0"]]
        return "", "", "", initial_context_data

    def copy_to_context(self, source_text: str, selected_text: str):
        """Copy selected text from preparation to context area and track indices."""
        # Determine what text to copy
        text_to_copy = selected_text if selected_text.strip() else source_text
        
        if not text_to_copy.strip():
            gr.Warning("No text to copy.")
            return "", ""
        
        # Find the selected text in source and calculate indices
        if text_to_copy != source_text and text_to_copy.strip():
            start_idx = source_text.find(text_to_copy)
            if start_idx != -1:
                end_idx = start_idx + len(text_to_copy)
                self.selection_start = start_idx
                self.selection_end = end_idx
                index_info = f"Selection: {start_idx}:{end_idx}"
            else:
                # Selected text not found, use full text
                self.selection_start = 0
                self.selection_end = len(source_text)
                text_to_copy = source_text
                index_info = f"Selection: 0:{len(source_text)} (full text)"
        else:
            # Full text selected
            self.selection_start = 0
            self.selection_end = len(source_text)
            text_to_copy = source_text
            index_info = f"Selection: 0:{len(source_text)} (full text)"
        
        gr.Info(f"Text copied to context area (indices: {self.selection_start}:{self.selection_end})")
        # Return text and DataFrame data for context stats
        words = len(text_to_copy.split()) if text_to_copy else 0
        chars = len(text_to_copy)
        selection_range = f"{self.selection_start}:{self.selection_end}"
        context_data = [[words, chars, selection_range]]
        return text_to_copy, context_data

    def apply_modified(self, source_text: str, context_text: str, modification_text: str):
        """Apply modified text to replace the selected text in source using tracked indices."""
        if not context_text.strip():
            gr.Warning("No text selected in context area to replace.")
            return source_text
        
        if not modification_text.strip():
            gr.Warning("No modified text to apply.")
            return source_text
        
        # Validate that we have valid selection indices
        if self.selection_start < 0 or self.selection_end < 0 or self.selection_start >= len(source_text):
            gr.Warning("Invalid selection indices. Please select text again.")
            return source_text
        
        # Ensure indices are within bounds
        start_idx = max(0, self.selection_start)
        end_idx = min(len(source_text), self.selection_end)
        
        # Verify that the context text matches the selected region
        selected_region = source_text[start_idx:end_idx]
        if selected_region != context_text:
            gr.Warning("Context text doesn't match selected region. Source text may have changed.")
            return source_text
        
        # Replace the selected region with modified text
        new_source = source_text[:start_idx] + modification_text + source_text[end_idx:]
        self.document.update_text(new_source)
        
        # Reset selection indices after applying
        self.selection_start = 0
        self.selection_end = 0
        
        gr.Info(f"Modified text applied successfully at indices {start_idx}:{end_idx}")
        return new_source

    def get_word_count(self, text: str):
        return len(text.split()) if text else 0

    def _format_footnotes(self):
        if self.document.footnotes and len(self.document.footnotes) > 0:
            # Return DataFrame data with checkbox, index, and footnote columns
            return [[True, i, footnote] for i, footnote in enumerate(self.document.footnotes, 1)]
        return [[False, 0, "No footnotes available"]]

    def execute_action(self, multimodal_input, source_text: str, context_text: str, modification_text: str, selected_panel: str, url_input: str = ""):
        """Execute AI action based on multimodal input and selected panel."""
        if not multimodal_input:
            gr.Warning("Please provide input")
            return source_text, context_text, modification_text, self._format_footnotes(), multimodal_input
        
        # Extract and process input (audio + text)
        final_prompt = self._extract_prompt_from_multimodal(multimodal_input)
        
        if not final_prompt:
            gr.Warning("Please provide a text prompt or upload an audio file")
            return source_text, context_text, modification_text, self._format_footnotes(), {"text": "", "files": []}

        gr.Info(f"Processing: {final_prompt[:80]}...")
        
        if selected_panel == "preparation":
            gen_text, _, fnotes = self._generate_text(final_prompt, url_input.strip())
            return gen_text, context_text, modification_text, fnotes, {"text": "", "files": []}
        elif selected_panel == "modification":
            # In modification mode
            if context_text.strip() or modification_text.strip():
                # Modify existing text
                text_to_modify = context_text or modification_text
                if text_to_modify.strip():
                    mod_text, fnotes = self._modify_text(text_to_modify, final_prompt, source_text)
                    return source_text, context_text, mod_text, fnotes, {"text": "", "files": []}
                else:
                    gr.Warning("No text available to modify in modification mode.")
                    return source_text, context_text, modification_text, self._format_footnotes(), {"text": "", "files": []}
        else:
            return source_text, context_text, modification_text, self._format_footnotes(), {"text": "", "files": []}

    def _extract_prompt_from_multimodal(self, multimodal_input) -> str:
        """Extract and combine text prompt from multimodal input (audio + text)"""
        text_prompt = multimodal_input.get("text", "") if isinstance(multimodal_input, dict) else ""
        files = multimodal_input.get("files", []) if isinstance(multimodal_input, dict) else []
        
        # Process audio files
        transcribed_text = ""
        if files:
            supported_formats = get_supported_formats()
            for file_path in files:
                if file_path and Path(file_path).suffix.lower() in supported_formats:
                    print(f"Transcribing: {Path(file_path).name}")
                    transcription = self.audio_processor.process_audio_file(file_path)
                    if transcription:
                        transcribed_text += (" " + transcription.strip()) if transcribed_text else transcription.strip()
                else:
                    print(f"Unsupported format: {Path(file_path).suffix}")
        
        # Combine transcribed audio with text prompt
        return f"{transcribed_text} {text_prompt}".strip()

    def _generate_text(self, topic: str, url: str = ""):
        """Generate text with optional URL (URL scraping handled by preparation agent)"""
        
        # Generate text using preparation agent (it handles URL scraping internally)
        if url.strip():
            gr.Info(f"Processing with URL: {url}")
            result = self.prep_agent.generate_text(topic, url.strip())
        else:
            result = self.prep_agent.generate_text(topic)
        
        generated_text = result.get('text', '')
        
        # This generated text should go into the preparation text box
        self.document.update_footnotes(result.get('footnotes', []))
        
        word_count = result.get('word_count', 0)
        footnote_count = len(result.get('footnotes', []))
        
        if url.strip():
            print(f"Generated {word_count} words with {footnote_count} citations (including URL content)")
        else:
            print(f"Generated {word_count} words with {footnote_count} citations")
        
        # Return to source_text, clear document_text
        return generated_text, self.document.text, self._format_footnotes()

    def _modify_text(self, selected_text: str, prompt: str, document_text: str):
        if not selected_text.strip():
            print("No text selected or available in document to modify.")
            return document_text, self._format_footnotes()
        # The modification agent returns a string directly, not a dict
        modified_text = self.mod_agent.modify_text(document_text, selected_text, prompt)
        print("Text modified successfully")
        return modified_text, self._format_footnotes()

    def search_documents(self, query: str):
        """Search documents by summary and return matching filenames"""
        if not query.strip():
            return []
        
        matching_files = self.storage_manager.search_documents(query, limit=5)
        gr.Info(f"Found {len(matching_files)} documents matching '{query}'")
        return matching_files

    def load_document_to_preparation(self, display_name: str):
        """Load document from Weaviate to preparation panel"""
        if not display_name:
            gr.Warning("Please select a file")
            return "", self._format_footnotes()
        
        # Extract filename from display name (format: "filename (date)")
        if " (" in display_name:
            filename = display_name.split(" (")[0]
        else:
            filename = display_name
        
        doc = self.storage_manager.load_document(filename)
        if doc:
            self.document = doc
            gr.Info(f"Successfully loaded '{filename}' to preparation panel")
            # Load into source text (preparation panel)
            return doc.text, self._format_footnotes()
        else:
            gr.Warning(f"Document '{filename}' not found")
            return "", self._format_footnotes()

    def generate_from_url(self, url: str):
        """Generate content from URL using the new URL scraping workflow"""
        if not url.strip():
            gr.Warning("Please enter a URL")
            return "", self._format_footnotes(), []
        
        # Use the new _generate_text method with URL scraping
        default_prompt = f"Generate comprehensive content based on the information from this URL"
        generated_text, _, fnotes = self._generate_text(default_prompt, url.strip())
        
        word_count = len(generated_text.split()) if generated_text else 0
        footnote_count = len(self.document.footnotes)
        gr.Info(f"Generated {word_count} words with {footnote_count} citations from URL")
        
        return generated_text, fnotes, []

    def save_preparation_document(self, filename: str, source_text: str, footnotes_data=None):
        """Save document from preparation panel to Weaviate"""
        if not filename.strip():
            gr.Warning("Please enter a filename")
            return
        
        # Check if source text has content
        if not source_text.strip():
            gr.Warning("Cannot save empty document. Please add some content first.")
            return
        
        # Update document with current source text
        self.document.update_text(source_text)
        
        # Create a copy of the document for saving
        doc_to_save = TextDocument(
            text=source_text,
            footnotes=self.document.footnotes[:],  # Copy footnotes
            metadata=self.document.metadata.copy()
        )
        
        # Filter footnotes based on checkbox selection if footnotes_data is provided
        if footnotes_data is not None and hasattr(footnotes_data, '__len__') and len(footnotes_data) > 0:
            # Simple filter: get rows where Save column is True
            selected_rows = footnotes_data[footnotes_data['Save'] == True]
            selected_footnotes = selected_rows['References (Only modify this)'].tolist()
            
            print(f"DEBUG: Found {len(selected_footnotes)} selected footnotes")
            
            # Update the copy's footnotes with selected ones
            doc_to_save.footnotes = selected_footnotes
        else:
            print(f"DEBUG: No footnotes_data provided or empty")
        
        # Create summary and keywords for Weaviate
        summary = f"Document created with TechEU Editor - {source_text[:100]}..."
        keywords = ["aouxai", "editor", "document"]
        
        if self.storage_manager.save_document(doc_to_save, filename, summary, keywords):
            gr.Info(f"Successfully saved '{filename}' to Weaviate")
        else:
            gr.Warning("Failed to save document to Weaviate")

    def get_available_files(self) -> List[str]:
        return self.storage_manager.list_documents()

def create_interface():
    editor = TextEditor()
    
    # Register cleanup on exit
    def cleanup():
        if hasattr(editor.storage_manager, 'close'):
            editor.storage_manager.close()
        if hasattr(editor.audio_processor, 'close'):
            editor.audio_processor.close()
        if hasattr(editor.prep_agent, 'close'):
            editor.prep_agent.close()
        if hasattr(editor.mod_agent, 'close'):
            editor.mod_agent.close()
        print("All resources cleaned up")
    
    atexit.register(cleanup)

    css = """
        .main-header { 
            text-align: center; 
            margin-bottom: 1.5rem; 
        }
        .section-header { 
            border-bottom: 1px solid;
            padding-bottom: 0.5rem;
        }
        .highlight-box {
            display: inline-block;
            background: linear-gradient(135deg, #4285f4, #34a853);
            color: white;
            padding: 0.3rem 0.8rem;
            border-radius: 8px;
        }
    """

    with gr.Blocks(title="TechEU Editor", theme=gr.themes.Soft(), css=css, fill_width=True) as interface:
        # State variables for tracking selections and panel focus
        prep_selection = gr.State("")
        mod_selection = gr.State("")
        selected_panel = gr.State("preparation")

        gr.HTML("""
        <div class="main-header">
            <h2>TechEU <span class="highlight-box">Editor</span></h2>
            <p style="margin-top: 0.5rem; font-style: italic; color: #666;">AI-powered text generation and modification editor</p>
        </div>
        """)

        with gr.Accordion("File Management", open=False):
            gr.Markdown("**Load Document to Preparation Panel**")
            with gr.Row():
                search_query = gr.Textbox(
                    label="Search Documents",
                    placeholder="Enter search query to find documents...",
                    scale=3,
                    show_label=False,
                    container=False
                )
                search_btn = gr.Button("Search", variant="secondary")
            
            with gr.Row():
                file_dropdown = gr.Dropdown(
                    label="Select Document",
                    choices=editor.get_available_files(), 
                    scale=1, 
                    interactive=True,
                    show_label=False,
                    container=False,
                )
                load_btn = gr.Button("Load", variant="secondary")
            
            gr.Markdown("---")
            gr.Markdown("**Save Document**")
            with gr.Row():
                save_filename = gr.Textbox(
                    placeholder="Enter filename to save...", 
                    scale=4, 
                    show_label=False, 
                    container=False
                )
                save_btn = gr.Button("Save", variant="secondary")

        with gr.Group():
            with gr.Row():
                with gr.Column(scale=1):
                    with gr.Group():
                        prep_header = gr.Button("1. Preparation Mode", variant="primary", size="lg", elem_classes="section-header")
                        source_text = gr.Textbox(
                            label="Source",
                            placeholder="Generated text will appear here, or enter text to modify...",
                            lines=19,
                            max_lines=26,
                        )
                        with gr.Accordion("metadata", open=False):
                            source_stats = gr.DataFrame(
                                value=[[0, 0, 0]],
                                headers=["Words", "Characters", "Lines"],
                                datatype=["number", "number", "number"],
                                row_count=1,
                                col_count=3,
                                interactive=False,
                                wrap=True
                            )

                with gr.Column(scale=1):
                    with gr.Group():
                        mod_header = gr.Button("2. Modification Mode", variant="secondary", size="lg", elem_classes="section-header")
                        
                        # Context area (read-only, shows selected text from preparation)
                        context_text = gr.Textbox(
                            label="Context Area",
                            placeholder="Selected text from Preparation will appear here...",
                            lines=5,
                            max_lines=7,
                            interactive=False
                        )
                        with gr.Accordion("metadata", open=False):
                            context_stats = gr.DataFrame(
                                value=[[0, 0, "0:0"]],
                                headers=["Words", "Characters", "Selection"],
                                datatype=["number", "number", "str"],
                                row_count=1,
                                col_count=3,
                                interactive=False,
                                wrap=True
                            )

                        # Modification area (editable, shows generated/modified text)
                        modification_text = gr.Textbox(
                            label="Modified Text",
                            placeholder="Modified text will appear here...",
                            lines=8,
                            max_lines=13,
                        )
                        with gr.Accordion("metadata", open=False):
                            modification_stats = gr.DataFrame(
                                value=[[0, 0, 0]],
                                headers=["Words", "Characters", "Lines"],
                                datatype=["number", "number", "number"],
                                row_count=1,
                                col_count=3,
                                interactive=False,
                                wrap=True
                            )

            with gr.Row():
                new_btn = gr.Button("New", size="sm", variant="secondary")
                copy_btn = gr.Button("Copy Selected", size="sm", variant="secondary")
                apply_btn = gr.Button("Apply Modified", size="sm", variant="primary")
                clear_btn = gr.Button("Clear All", size="sm", variant="stop")

            with gr.Accordion("Footnotes & Citations", open=False):
                footnotes_display = gr.Dataframe(
                    value=[[False, 0, "No footnotes available"]],
                    headers=["Save", "Index", "References (Only modify this)"],
                    datatype=["bool", "number", "str"],
                    col_count=(3, "fixed"),
                    row_count=(1, "dynamic"),
                    wrap=True,
                    column_widths=["10%", "10%", "80%"]
                )

        # Get supported audio formats for display
        supported_formats = get_supported_formats()
        formats_text = ", ".join(supported_formats)
        
        with gr.Group():
            url_input = gr.Textbox(
                label="URL",
                placeholder="https://",
                container=True,
                show_label=False,
                scale=1
            )
            
            multimodal_input = gr.MultimodalTextbox(
                interactive=True,
                file_count="multiple",
                placeholder=f"Provide a text prompt \nOr \nUpload audio files ({formats_text}) \nOr \nRecord audio using microphone",
                lines=3,
                container=False,
                show_label=False,
                sources=["microphone", "upload"],
                submit_btn=True
            )

        # Event Handlers
        def update_counts(source, context, modification):
            source_words = editor.get_word_count(source)
            source_chars = len(source) if source else 0
            source_lines = source.count('\n') + 1 if source else 0
            
            context_words = editor.get_word_count(context)
            context_chars = len(context) if context else 0
            # Use the actual selection indices from the editor
            selection_range = f"{editor.selection_start}:{editor.selection_end}" if editor.selection_start != 0 or editor.selection_end != 0 else "0:0"
            
            modification_words = editor.get_word_count(modification)
            modification_chars = len(modification) if modification else 0
            modification_lines = modification.count('\n') + 1 if modification else 0
            
            source_data = [[source_words, source_chars, source_lines]]
            context_data = [[context_words, context_chars, selection_range]]
            modification_data = [[modification_words, modification_chars, modification_lines]]
            
            return source_data, context_data, modification_data

        # Update statistics when text changes
        source_text.change(update_counts, 
                          inputs=[source_text, context_text, modification_text], 
                          outputs=[source_stats, context_stats, modification_stats])
        context_text.change(update_counts, 
                           inputs=[source_text, context_text, modification_text], 
                           outputs=[source_stats, context_stats, modification_stats])
        modification_text.change(update_counts, 
                                inputs=[source_text, context_text, modification_text], 
                                outputs=[source_stats, context_stats, modification_stats])
        
        # Handle text selection and panel mode switching via header buttons
        def handle_prep_select(evt: gr.SelectData):
            # Auto-switch to preparation mode when clicking source text
            return evt.value if hasattr(evt, 'value') else "", "preparation", gr.update(variant="primary"), gr.update(variant="secondary")
        
        def handle_mod_select(evt: gr.SelectData):
            # Auto-switch to modification mode when clicking modification text
            return evt.value if hasattr(evt, 'value') else "", "modification", gr.update(variant="secondary"), gr.update(variant="primary")
        
        def handle_prep_mode():
            return "preparation", gr.update(variant="primary"), gr.update(variant="secondary")
        
        def handle_mod_mode():
            return "modification", gr.update(variant="secondary"), gr.update(variant="primary")
        
        # Set up selection handlers for text areas with auto mode switching
        source_text.select(handle_prep_select, outputs=[prep_selection, selected_panel, prep_header, mod_header])
        modification_text.select(handle_mod_select, outputs=[mod_selection, selected_panel, prep_header, mod_header])
        
        # Also handle clicks (focus) on text areas to switch modes
        source_text.focus(handle_prep_mode, outputs=[selected_panel, prep_header, mod_header])
        modification_text.focus(handle_mod_mode, outputs=[selected_panel, prep_header, mod_header])
        
        # Set up mode selection via header buttons with visual feedback
        prep_header.click(handle_prep_mode, outputs=[selected_panel, prep_header, mod_header])
        mod_header.click(handle_mod_mode, outputs=[selected_panel, prep_header, mod_header])

        # Button event handlers
        new_btn.click(editor.new_document, outputs=[source_text, context_text, modification_text, footnotes_display, context_stats])
        copy_btn.click(editor.copy_to_context, inputs=[source_text, prep_selection], outputs=[context_text, context_stats])
        apply_btn.click(editor.apply_modified, inputs=[source_text, context_text, modification_text], outputs=[source_text])
        clear_btn.click(editor.clear_document, outputs=[source_text, context_text, modification_text, context_stats])
        
        def handle_execute_action(multimodal_input, source, context, modification, panel, url):
            if not multimodal_input:
                return source, context, modification, editor._format_footnotes(), {"text": "", "files": []}
            
            # Execute action based on selected panel
            new_source, new_context, new_modification, fnotes, updated_multimodal = editor.execute_action(
                multimodal_input, source, context, modification, panel, url
            )
            
            return new_source, new_context, new_modification, fnotes, updated_multimodal

        multimodal_input.submit(
            handle_execute_action,
            inputs=[multimodal_input, source_text, context_text, modification_text, selected_panel, url_input],
            outputs=[source_text, context_text, modification_text, footnotes_display, multimodal_input]
        )
        
        def save_and_refresh(filename, footnotes_data, source_text):
            # Save document from preparation panel
            editor.save_preparation_document(filename, source_text, footnotes_data)
            return gr.update()

        def search_and_update_dropdown(query):
            # Search documents and update dropdown
            matching_files = editor.search_documents(query)
            return gr.update(choices=matching_files, value=None)

        # Event handlers for new file management system
        search_btn.click(search_and_update_dropdown, inputs=[search_query], outputs=[file_dropdown])
        search_query.submit(search_and_update_dropdown, inputs=[search_query], outputs=[file_dropdown])
        load_btn.click(editor.load_document_to_preparation, inputs=[file_dropdown], outputs=[source_text, footnotes_display])
        url_input.submit(editor.generate_from_url, inputs=[url_input], outputs=[source_text, footnotes_display, file_dropdown])
        save_btn.click(save_and_refresh, inputs=[save_filename, footnotes_display, source_text], outputs=[file_dropdown])
    
    return interface

def main():
    interface = create_interface()
    interface.launch(server_port=7860)

if __name__ == "__main__":
    main()

class PromptBuilderService:
    """Builds deterministic prompts for context-grounded RAG generation."""

    @staticmethod
    def build(question: str, context_chunks: list[dict], conversation_history: str = '') -> str:
        """Create a production-safe prompt with explicit grounding instructions."""
        rendered_context = []
        for index, chunk in enumerate(context_chunks, start=1):
            chunk_text = ' '.join(chunk['content'].split())
            rendered_context.append(
                (
                    f"[{index}] "
                    f"Document: {chunk['file_name']}\n"
                    f"Excerpt: {chunk_text[:1500]}"
                )
            )

        context_block = '\n\n'.join(rendered_context)
        question_lower = question.lower()

        # Plain text prompt — Ollama applies each model's native template on top,
        # so using model-specific tags (ChatML, Llama3, etc.) would double-wrap.
        history_section = ''
        if conversation_history.strip():
            history_section = (
                f'Prior conversation (for context only — do NOT use as factual answers):\n'
                f'{conversation_history.strip()}\n\n'
            )

        style_hint = ''
        if any(token in question_lower for token in ['explain', 'why', 'how', 'detail', 'detailed', 'elaborate']):
            style_hint = (
                'For this question, provide a complete explanation in this order:\n'
                '1) a short direct overview,\n'
                '2) key points in bullets,\n'
                '3) a compact example based only on the Context if available.\n'
                'Do not stop after one point when the Context has more relevant details.\n\n'
            )

        return (
            f'You are a helpful, intelligent assistant. Answer the user\'s question using ONLY '
            f'the information in the Context section below. Do not invent or assume facts not present in the Context.\n\n'
            f'How to answer:\n'
            f'- Be direct and conversational. Match the answer style to the question.\n'
            f'  • Simple questions (yes/no, who, what year) → one or two clear sentences.\n'
            f'  • Questions asking for a list or summary → use bullet points with **bold** labels.\n'
            f'  • Never use bullet points just for a single fact.\n'
            f'- Use **bold** only for genuinely important terms, not every phrase.\n'
            f'- If you cite a document, use backticks: `filename.pdf`.\n'
            f'- Do NOT add disclaimers, caveats, or meta-commentary when you have a clear answer.\n'
            f'- If and ONLY IF the Context contains absolutely no relevant information, '
            f'respond with exactly one sentence: "I could not find that in the document." '
            f'Do not append this to an answer you have already given.\n\n'
            f'{style_hint}'
            f'{history_section}'
            f'Context:\n{context_block}\n\n'
            f'Question: {question}\n'
            f'Answer:'
        )

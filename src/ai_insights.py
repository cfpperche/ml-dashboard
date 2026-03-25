"""Claude AI Insights — usa Claude Agent SDK com OAuth da assinatura."""
import asyncio
import os
import json
from dotenv import load_dotenv

load_dotenv()


async def analyze_with_claude(prompt: str, data_context: str = "") -> str:
    """
    Envia prompt + dados para Claude via Agent SDK (usa OAuth token da assinatura).
    Fallback para subprocess se o SDK não funcionar.
    """
    full_prompt = prompt
    if data_context:
        full_prompt = f"{prompt}\n\nDados para análise:\n{data_context}"

    # Tenta via Agent SDK primeiro
    try:
        return await _query_sdk(full_prompt)
    except Exception as e:
        print(f"SDK falhou ({e}), tentando via CLI...")

    # Fallback: Claude CLI como subprocesso (sempre funciona com OAuth)
    try:
        return await _query_cli(full_prompt)
    except Exception as e:
        return f"Erro ao consultar Claude: {e}"


async def _query_sdk(prompt: str) -> str:
    """Consulta via claude-agent-sdk Python (requer CLAUDE_CODE_OAUTH_TOKEN)."""
    from claude_agent_sdk import query, ClaudeAgentOptions

    options = ClaudeAgentOptions(
        system_prompt=(
            "Você é um analista especialista em e-commerce e peças de servidor. "
            "Analise os dados fornecidos e dê insights acionáveis em português. "
            "Seja direto, use números, identifique oportunidades e riscos."
        ),
        max_turns=1,
    )

    result_parts = []
    async for message in query(prompt=prompt, options=options):
        if hasattr(message, "content"):
            for block in message.content:
                if hasattr(block, "text"):
                    result_parts.append(block.text)
        elif hasattr(message, "result"):
            result_parts.append(str(message.result))

    return "\n".join(result_parts) if result_parts else "Sem resposta do Claude."


async def _query_cli(prompt: str) -> str:
    """Fallback: executa `claude -p` como subprocesso (usa OAuth da sessão)."""
    proc = await asyncio.create_subprocess_exec(
        "claude", "-p", prompt, "--output-format", "text",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode == 0:
        return stdout.decode("utf-8").strip()
    else:
        raise RuntimeError(f"CLI error: {stderr.decode('utf-8')[:500]}")


def format_products_for_analysis(products: list[dict]) -> str:
    """Formata lista de produtos do ML para enviar ao Claude."""
    if not products:
        return "Nenhum produto encontrado."

    lines = []
    for i, p in enumerate(products[:30], 1):  # limita a 30 pra não estourar contexto
        lines.append(
            f"{i}. {p.get('title','')} | "
            f"R$ {p.get('price', 0):,.2f} | "
            f"Vendedor: {p.get('seller', {}).get('nickname', '?')} | "
            f"Frete grátis: {p.get('shipping', {}).get('free_shipping', '?')} | "
            f"Condição: {p.get('condition', '?')}"
        )
    return "\n".join(lines)

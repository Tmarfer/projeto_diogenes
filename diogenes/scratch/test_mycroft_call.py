import sys
import os
import time
from pathlib import Path

# Add src to python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from diogenes.config import get_config
from diogenes.llm.base import get_llm_client
from diogenes.agents.mycroft import MycrooftAgent
from diogenes.models import WatsonOutput

# Load config
cfg = get_config()
cycle_id = "MOD_010_A1_20260604T174612Z"
cycle_dir = cfg.workspace.path / "cycles" / cycle_id
docs_dir = Path(__file__).resolve().parent.parent / "docs" / "agentes"

# Read previous Watson output
apresentacao_path = cycle_dir / "stranger_room" / "watson_integridade" / "01_apresentacao.md"
if not apresentacao_path.exists():
    print(f"Error: Previous Watson output not found at {apresentacao_path}")
    sys.exit(1)

apresentacao_texto = apresentacao_path.read_text(encoding="utf-8")
print(f"Read Watson output presentation ({len(apresentacao_texto)} chars).")

# Initialize LLM Client and Mycroft
runtime_dir = cycle_dir / "_runtime"
llm = get_llm_client(cycle_id, runtime_dir)

mycroft = MycrooftAgent(
    llm=llm,
    agent_spec=cfg.agentes.mycroft,
    cycle_id=cycle_id,
    docs_dir=docs_dir / "mycroft",
    cycle_dir=cycle_dir
)

# Prepare WatsonOutput
watson_output = WatsonOutput(
    texto=apresentacao_texto,
    critical_alerts_count=6,
    has_unanalyzable_files=False,
    secoes={}
)

# Clear last line of llm_calls.jsonl if it exists, to read the new one
llm_log_path = runtime_dir / "llm_calls.jsonl"
initial_lines_count = 0
if llm_log_path.exists():
    initial_lines_count = len(llm_log_path.read_text(encoding="utf-8").splitlines())

print("Calling Mycroft.avaliar_watson...")
t0 = time.monotonic()
try:
    result = mycroft.avaliar_watson(watson_output, fase="watson_integridade", rodada=0)
    elapsed = time.monotonic() - t0
    print(f"\n--- SUCCESS ---")
    print(f"Elapsed Time: {elapsed:.2f}s")
    print(f"Result Type: {result.tipo}")
    print(f"Result Text Length: {len(result.texto)} chars")
    
    # Read token metrics
    if llm_log_path.exists():
        lines = llm_log_path.read_text(encoding="utf-8").splitlines()
        if len(lines) > initial_lines_count:
            last_call = lines[-1]
            import json
            call_data = json.loads(last_call)
            print(f"Prompt Tokens: {call_data.get('prompt_tokens')}")
            print(f"Completion Tokens: {call_data.get('completion_tokens')}")
            print(f"Custo Ref USD: {call_data.get('cost_usd')}")
except Exception as e:
    print(f"\n--- FAILURE ---")
    print(f"Error: {e}")

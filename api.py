from fastapi import FastAPI
import banco

app = FastAPI()

@app.get("/dados")
def get_dados(armazem_id: int = 1):
    notas = banco.ler_notas(armazem_id)
    duplas = banco.ler_duplas(armazem_id)
    
    # Criamos uma lista organizada de dados para enviar ao frontend
    resultado = []
    ruas = banco.listar_ruas(armazem_id)
    
    for rua in ruas:
        resultado.append({
            "rua": rua,
            "nota": notas.get(rua, 0.0),
            "dupla": duplas.get(rua, "Sem dupla")
        })
    return {"status": "sucesso", "armazem_id": armazem_id, "dados": resultado}
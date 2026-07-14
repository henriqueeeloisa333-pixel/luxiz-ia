from fastapi import FastAPI
import banco

app = FastAPI()

@app.get("/dados")
def get_dados():
    notas = banco.ler_notas()
    duplas = banco.ler_duplas()
    
    # Criamos uma lista organizada de dados para enviar ao frontend
    resultado = []
    ruas = ["Rua 01", "Rua 02", "Rua 03", "Rua 04", "Rua 05", "Rua 06", "Rua 07", "Rua 35&32", "Rua 33&34"]
    
    for rua in ruas:
        resultado.append({
            "rua": rua,
            "nota": notas.get(rua, 0.0),
            "dupla": duplas.get(rua, "Sem dupla")
        })
    return {"status": "sucesso", "dados": resultado}
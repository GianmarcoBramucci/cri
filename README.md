# CRI

## Struttura del Progetto

```
cri/
├── app/
│   ├── api/
│   │   ├── router.py       # Endpoints FastAPI
│   │   └── models.py       # Modelli Pydantic
│   ├── core/
│   │   ├── config.py       # Gestione configurazioni
│   │   └── logging.py      # Setup logging
│   ├── rag/
│   │   ├── engine.py       # Pipeline RAG
│   │   ├── memory.py       # Gestione memoria conversazioni
│   │   └── prompts.py      # Template dei prompt
│   └── utils/
│       └── helpers.py      # Funzioni di utilità
├── main.py                 # Entry point applicazione
├── .env.example            # Esempio variabili d'ambiente
├── requirements.txt        # Dipendenze del progetto
├── README.md               # Documentazione
└── .gitignore
```
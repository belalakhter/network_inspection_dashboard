## Project Structure

```text
finance_trend_analyzer/
├── app/                    # FastAPI application and UI
│   ├── main.py             # Main REST API entry point
│   ├── schemas.py          # Pydantic models for API
│   └── static/             # Static UI assets
│       └── index.html      # Prediction Dashboard
├── model/                  # PyTorch model logic
│   ├── model.py            # Transformer implementation
│   ├── train.py            # Training and MLflow logging
│   └── dataset.py          # Data ingestion and indicators
├── deployment/             # Infrastructure manifests
│   ├── kserve/             # KServe InferenceService yaml
│   ├── k3s/                # Kubernetes core manifests
│   └── mlflow/             # MLflow server configuration
├── setup/                  # Workflow automation
│   ├── setup_k3s.sh        # K3s cluster initialization
│   └── deploy.sh           # CI/CD deployment logic
├── requirements.txt        # Python dependency list
└── README.md               # Project documentation
```


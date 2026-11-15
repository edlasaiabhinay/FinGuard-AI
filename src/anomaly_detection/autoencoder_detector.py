
import numpy as np
import torch
import torch.nn as nn


class InvoiceAutoencoder(nn.Module):
    def __init__(self, input_dim):
        super().__init__()

        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 8)
        )

        self.decoder = nn.Sequential(
            nn.Linear(8, 16),
            nn.ReLU(),
            nn.Linear(16, 32),
            nn.ReLU(),
            nn.Linear(32, input_dim)
        )

    def forward(self, x):
        encoded = self.encoder(x)
        return self.decoder(encoded)


def reconstruction_errors(model, values, device):
    model.eval()

    tensor = torch.tensor(
        np.asarray(values, dtype=np.float32),
        dtype=torch.float32,
        device=device
    )

    with torch.no_grad():
        reconstructed = model(tensor)
        errors = torch.mean(
            (tensor - reconstructed) ** 2,
            dim=1
        )

    return errors.cpu().numpy()


def predict_autoencoder(
    model,
    scaler,
    features,
    threshold,
    feature_names,
    device
):
    row = np.array(
        [[features[name] for name in feature_names]],
        dtype=np.float32
    )

    scaled = scaler.transform(row)

    error = float(
        reconstruction_errors(model, scaled, device)[0]
    )

    return {
        "prediction": "ANOMALY" if error > threshold else "NORMAL",
        "is_anomaly": bool(error > threshold),
        "reconstruction_error": error,
        "threshold": float(threshold)
    }

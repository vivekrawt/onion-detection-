"""Prompt-ensemble CLIP inference; no training or custom weights."""
import torch
import torch.nn.functional as F
from transformers import CLIPModel, CLIPProcessor
from ..config import Settings
from ..vision.crops import square_pad
from .evidence import EVIDENCE_PROMPTS, detail_views, decide


class ClipClassifier:
    def __init__(self, config: Settings):
        self.config = config
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        options = {"local_files_only": config.LOCAL_FILES_ONLY, "cache_dir": str(config.MODEL_CACHE_DIR)}
        self.processor = CLIPProcessor.from_pretrained(config.CLIP_MODEL_NAME, use_fast=False, **options)
        self.model = CLIPModel.from_pretrained(config.CLIP_MODEL_NAME, **options).to(self.device).eval()
        self.classes = list(config.CLASS_PROMPTS)
        # Cache normalized mean text embeddings once, instead of recomputing per onion.
        with torch.inference_mode():
            features = []
            for prompts in config.CLASS_PROMPTS.values():
                inputs = self.processor(text=prompts, return_tensors="pt", padding=True).to(self.device)
                embedding = self.model.get_text_features(**inputs)
                features.append(F.normalize(embedding, dim=-1).mean(dim=0))
            self.text_features = F.normalize(torch.stack(features), dim=-1)
            self.evidence_keys = []
            evidence = []
            for key, prompts in EVIDENCE_PROMPTS.items():
                inputs = self.processor(text=prompts, return_tensors='pt', padding=True).to(self.device)
                evidence.append(F.normalize(self.model.get_text_features(**inputs), dim=-1))
                self.evidence_keys.extend([key] * len(prompts))
            self.evidence_features = torch.cat(evidence)

    def classify(self, images):
        results = []
        if not images:
            return results
        # Six views per target preserve the full crop and inspect smaller visible
        # details. Encode them in bounded batches to avoid loading a lot at once.
        views = [view for image in images for view in detail_views(image)]
        encoded = []
        with torch.inference_mode():
            for offset in range(0, len(views), self.config.BATCH_SIZE):
                batch = [square_pad(image) for image in views[offset:offset + self.config.BATCH_SIZE]]
                inputs = self.processor(images=batch, return_tensors="pt").to(self.device)
                encoded.append(F.normalize(self.model.get_image_features(**inputs), dim=-1))
            embeddings = torch.cat(encoded).reshape(len(images), 6, -1)
            similarities = embeddings[:, 0] @ self.text_features.T
            scores = (similarities * self.model.logit_scale.exp()).softmax(dim=-1)
            evidence = (embeddings @ self.evidence_features.T).cpu().tolist()
            for cosine, relative, evidence_views in zip(similarities.cpu().tolist(), scores.cpu().tolist(), evidence):
                best = max(range(len(relative)), key=relative.__getitem__)
                prediction = {
                    "predicted_class": self.classes[best],
                    "condition": self.classes[best],
                    "needs_review": relative[best] < self.config.CLIP_CONFIDENCE_THRESHOLD,
                    "confidence": relative[best],
                    "scores": dict(zip(self.classes, relative)),
                    "similarities": dict(zip(self.classes, cosine)),
                }
                checks = [{key: max(value for label, value in zip(self.evidence_keys, values) if label == key)
                           for key in EVIDENCE_PROMPTS} for values in evidence_views]
                results.append(decide(prediction, checks, self.config))
        return results

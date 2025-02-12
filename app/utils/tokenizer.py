from app import app
import sentencepiece as spm
import os
import subprocess

class Tokenizer:
    def __init__(self, engine):
        self.sp = None
        self.loaded = False
        self.path = engine.path
        self.src_lang = engine.source.code 
        self.trg_lang = engine.target.code

    def load(self):
        if not self.sp:
            model_file = os.path.join(self.path, f"vocab.{self.src_lang}{self.trg_lang}.spm")
            self.sp = spm.SentencePieceProcessor(model_file=model_file)
            
    def tokenize(self, text):
        if self.sp:
            return " ".join(self.sp.encode(text, out_type=str))
        return None
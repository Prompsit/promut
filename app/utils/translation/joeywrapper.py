# Inspired in https://github.com/juliakreutzer/slack-joey/blob/master/bot.py

from app import app
from app.utils.GPUManager import GPUManager

#from torchtext.legacy import data
#from torchtext.legacy.data import Dataset, Iterator, Field

#from joeynmt.helpers import load_config, get_latest_checkpoint, load_checkpoint
#from joeynmt.vocabulary import build_vocab
#from joeynmt.model import build_model
#from joeynmt.prediction import validate_on_data
#from joeynmt.constants import UNK_TOKEN, EOS_TOKEN, BOS_TOKEN, PAD_TOKEN

import os
import logging
import sys
import time

class MonoLineDataset():
    @staticmethod
    def sort_key(ex):
        return None

class JoeyWrapper:
    def __init__(self, engine_path, is_admin):
        return None

    def load(self):
        return None

    def load_line_as_data(self, line, level, lowercase, src_vocab, trg_vocab):
        return None

    def joey_translate(self, message_text, model, src_vocab, trg_vocab,
              logger, beam_size, beam_alpha, level, lowercase,
              max_output_length, use_cuda, nbest, cuda_device):

       return None

    def translate(self, line, nbest=1):
        return None 

"""
class MonoLineDataset(Dataset):
    @staticmethod
    def sort_key(ex):
        return len(ex.src)

    def __init__(self, line: str, field: Field, **kwargs) -> None:
        fields = [('src', field)]
        examples = [data.Example.fromlist([line], fields)]

        super(MonoLineDataset, self).__init__(examples, fields, **kwargs)

class JoeyWrapper:
    def __init__(self, engine_path, is_admin):
        self.engine_path = engine_path
        self.is_admin = is_admin
        self.model_path = os.path.join(engine_path, 'model')
        self.config_path = os.path.join(engine_path, 'config.yaml')
        self.gpu_id = None
        
        # Load parameters from configuration file
        config = load_config(self.config_path)

        if "load_model" in config['training'].keys():
            self.ckpt = os.path.realpath(os.path.join(app.config['JOEYNMT_FOLDER'], config['training']["load_model"]))
        else:
            self.ckpt = get_latest_checkpoint(self.model_path)

        self.use_cuda = config["training"].get("use_cuda", False)
        self.level = config["data"]["level"]
        self.max_output_length = config["training"].get("max_output_length", None)
        self.lowercase = config["data"].get("lowercase", False)
        self.model_data = config["model"]

        # load the vocabularies
        src_vocab_file = os.path.realpath(os.path.join(app.config['JOEYNMT_FOLDER'], config["data"]["src_vocab"]))
        trg_vocab_file = os.path.realpath(os.path.join(app.config['JOEYNMT_FOLDER'], config["data"]["trg_vocab"]))
        self.src_vocab = build_vocab(field="src", vocab_file=src_vocab_file,
                                dataset=None, max_size=-1, min_freq=0)
        self.trg_vocab = build_vocab(field="trg", vocab_file=trg_vocab_file,
                                dataset=None, max_size=-1, min_freq=0)

        # whether to use beam search for decoding, 0: greedy decoding
        if "testing" in config.keys():
            self.beam_size = config["testing"].get("beam_size", 0)
            self.beam_alpha = config["testing"].get("alpha", -1)
        else:
            self.beam_size = 1
            self.beam_alpha = -1
        
        self.logger = logging.getLogger(__name__)

    def load(self):
        # build model and load parameters into it
        model_checkpoint = load_checkpoint(self.ckpt, self.use_cuda)
        self.model = build_model(self.model_data, src_vocab=self.src_vocab, trg_vocab=self.trg_vocab)
        self.model.load_state_dict(model_checkpoint["model_state"])

        device = list(self.model.parameters())[0].device
        logging.debug("Loaded model in device: " + str(device))

        if self.use_cuda:
            # Move model to GPU
            self.gpu_id = os.environ["CUDA_VISIBLE_DEVICES"]
            if not os.environ["CUDA_VISIBLE_DEVICES" ]:
                return False
            else:
                # Assuming always one device in CUDA_VISIBLE_DEVICES
                # so moving to id 0, which is the only one
                self.model = self.model.to(0)
                device = list(self.model.parameters())[0].device
                logging.debug("Moved model to device: " + str(device))
        return True

    def load_line_as_data(self, line, level, lowercase, src_vocab, trg_vocab):
        tok_fun = lambda s: list(s) if level == "char" else s.split()

        src_field = data.Field(init_token=None, eos_token=EOS_TOKEN,  # FIXME
                            pad_token=PAD_TOKEN, tokenize=tok_fun,
                            batch_first=True, lower=lowercase,
                            unk_token=UNK_TOKEN,
                            include_lengths=True)
        trg_field = data.Field(init_token=BOS_TOKEN, eos_token=EOS_TOKEN,
                            pad_token=PAD_TOKEN, tokenize=tok_fun,
                            unk_token=UNK_TOKEN,
                            batch_first=True, lower=lowercase,
                            include_lengths=True)

        test_data = MonoLineDataset(line=line, field=src_field)
        src_field.vocab = src_vocab
        trg_field.vocab = trg_vocab

        return test_data, src_vocab, trg_vocab

    def joey_translate(self, message_text, model, src_vocab, trg_vocab,
              logger, beam_size, beam_alpha, level, lowercase,
              max_output_length, use_cuda, nbest, cuda_device):

        sentence = message_text.strip()
        if lowercase:
            sentence = sentence.lower()

        # load the data which consists only of this sentence
        test_data, src_vocab, trg_vocab = self.load_line_as_data(lowercase=lowercase,
            line=sentence, src_vocab=src_vocab, trg_vocab=trg_vocab, level=level)

        # generate outputs
        score, loss, ppl, sources, sources_raw, references, hypotheses, \
        hypotheses_raw, attention_scores = validate_on_data(
            model=model, data=test_data, batch_size=1, level=level,
            max_output_length=max_output_length, eval_metric=None,
            use_cuda=use_cuda, beam_size=beam_size,
            beam_alpha=beam_alpha, n_best=nbest, cuda_device=cuda_device, n_gpu=1)

        return hypotheses[0] if nbest == 1 else hypotheses

    def translate(self, line, nbest=1):
        line = line.strip()
        cuda_device = 0 if os.environ["CUDA_VISIBLE_DEVICES"] else self.gpu_id
        #cuda_device = self.gpu_id
        if line:
            return self.joey_translate(line,
                            beam_size=self.beam_size,
                            beam_alpha=self.beam_alpha,
                            level=self.level,
                            lowercase=self.lowercase,
                            max_output_length=self.max_output_length,
                            model=self.model,
                            src_vocab=self.src_vocab,
                            trg_vocab=self.trg_vocab,
                            use_cuda=self.use_cuda,
                            logger=self.logger,
                            nbest=nbest,
                            cuda_device=cuda_device)
        else:
            return None
"""

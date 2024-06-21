import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import torch
import torchaudio
from torch import nn

import onnxruntime

import os
from text import cleaned_text_to_sequence
# from text.japanese import g2p
from text.chinese import g2p,text_normalize
# from text.english import g2p
import soundfile

import ffmpeg
import numpy as np
import librosa
from my_utils import load_audio

ONNX_FOLDER_PATH = "/Users/donkeyddddd/Documents/Rx_projects/git_projects/GPT_Sovits_cmdline/onnx"
MODEL_FOLDER_PATH = "/Users/donkeyddddd/Documents/Rx_projects/git_projects/GPT_Sovits_cmdline/hugginface_model/parrots-gpt-sovits-speaker"
ONNX_SPEAKER_NAME = "MaiMai"

class T2SModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.hz = 50
        self.max_sec = 54
        self.top_k = 5
        self.early_stop_num = torch.LongTensor([self.hz * self.max_sec])
        
        self.sess_encoder = onnxruntime.InferenceSession(os.path.join(ONNX_FOLDER_PATH,ONNX_SPEAKER_NAME,ONNX_SPEAKER_NAME+"_t2s_encoder.onnx"), providers=["CPUExecutionProvider"])
        self.sess_fsdec = onnxruntime.InferenceSession(os.path.join(ONNX_FOLDER_PATH,ONNX_SPEAKER_NAME,ONNX_SPEAKER_NAME+"_t2s_fsdec.onnx"), providers=["CPUExecutionProvider"])
        self.sess_sdec = onnxruntime.InferenceSession(os.path.join(ONNX_FOLDER_PATH,ONNX_SPEAKER_NAME,ONNX_SPEAKER_NAME+"_t2s_sdec.onnx"), providers=["CPUExecutionProvider"])
        # self.sess_encoder = onnxruntime.InferenceSession(f"./onnx/plasticfork1/plasticfork1_t2s_encoder.onnx", providers=["CPUExecutionProvider"])
        # self.sess_fsdec = onnxruntime.InferenceSession(f"./onnx/plasticfork1/plasticfork1_t2s_fsdec.onnx", providers=["CPUExecutionProvider"])
        # self.sess_sdec = onnxruntime.InferenceSession(f"./onnx/plasticfork1/plasticfork1_t2s_sdec.onnx", providers=["CPUExecutionProvider"])

    def forward(self, ref_seq, text_seq, ref_bert, text_bert, ssl_content):
        early_stop_num = self.early_stop_num

        EOS = 1024

        #[1,N] [1,N] [N, 1024] [N, 1024] [1, 768, N]
        x, prompts = self.sess_encoder.run(None, {"ref_seq":ref_seq.detach().numpy(), "text_seq":text_seq.detach().numpy(), "ref_bert":ref_bert.detach().numpy(), "text_bert":text_bert.detach().numpy(), "ssl_content":ssl_content.detach().numpy()})
        x = torch.from_numpy(x)
        prompts = torch.from_numpy(prompts)

        prefix_len = prompts.shape[1]

        #[1,N,512] [1,N]
        y, k, v, y_emb, x_example = self.sess_fsdec.run(None, {"x":x.detach().numpy(), "prompts":prompts.detach().numpy()})
        y = torch.from_numpy(y)
        k = torch.from_numpy(k)
        v = torch.from_numpy(v)
        y_emb = torch.from_numpy(y_emb)
        x_example = torch.from_numpy(x_example)

        stop = False
        for idx in range(1, 1500):
            #[1, N] [N_layer, N, 1, 512] [N_layer, N, 1, 512] [1, N, 512] [1] [1, N, 512] [1, N]
            y, k, v, y_emb, logits, samples = self.sess_sdec.run(None, {"iy":y.detach().numpy(), "ik":k.detach().numpy(), "iv":v.detach().numpy(), "iy_emb":y_emb.detach().numpy(), "ix_example":x_example.detach().numpy()})
            y = torch.from_numpy(y)
            k = torch.from_numpy(k)
            v = torch.from_numpy(v)
            y_emb = torch.from_numpy(y_emb)
            logits = torch.from_numpy(logits)
            samples = torch.from_numpy(samples)
            if early_stop_num != -1 and (y.shape[1] - prefix_len) > early_stop_num:
                stop = True
            if torch.argmax(logits, dim=-1)[0] == EOS or samples[0, 0] == EOS:
                stop = True
            if stop:
                break
        y[0, -1] = 0

        return y[:, -idx:-1].unsqueeze(0)


class GptSoVits(nn.Module):
    def __init__(self, t2s):
        super().__init__()
        self.t2s = t2s
        self.sess = onnxruntime.InferenceSession(os.path.join(ONNX_FOLDER_PATH,ONNX_SPEAKER_NAME,ONNX_SPEAKER_NAME+"_vits.onnx"), providers=["CPUExecutionProvider"])

    def forward(self, ref_seq, text_seq, ref_bert, text_bert, ref_audio, ssl_content):
        pred_semantic = self.t2s(ref_seq, text_seq, ref_bert, text_bert, ssl_content)
        audio1 = self.sess.run(None, {
            "text_seq" : text_seq.detach().cpu().numpy(),
            "pred_semantic" : pred_semantic.detach().cpu().numpy(), 
            "ref_audio" : ref_audio.detach().cpu().numpy()
        })
        return torch.from_numpy(audio1[0])


class SSLModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.sess = onnxruntime.InferenceSession(os.path.join(ONNX_FOLDER_PATH,ONNX_SPEAKER_NAME,ONNX_SPEAKER_NAME+"_cnhubert.onnx"), providers=["CPUExecutionProvider"])

    def forward(self, ref_audio_16k):
        last_hidden_state = self.sess.run(None, {
            "ref_audio_16k" : ref_audio_16k.detach().cpu().numpy()
        })
        return torch.from_numpy(last_hidden_state[0])


def inference():
    gpt = T2SModel()
    gpt_sovits = GptSoVits(gpt)
    ssl = SSLModel()

    ref_audio = torch.randn((1, 48000 * 5)).float()

    # input_audio = os.path.join(MODEL_FOLDER_PATH,ONNX_SPEAKER_NAME,"ref.wav")
    input_audio = "/Users/donkeyddddd/Documents/Rx_projects/git_projects/GPT_Sovits_cmdline/input_audio/plasticfork_4s.wav"

    # ref_phones = g2p("水をマレーシアから買わなくてはならない。")
    ref_text = "嗯未来呢，我想继续忠实记录自己的生活。"
    # ref_text = "那我们，唠也唠了这么久了唠了有十几分钟了我们要不来唱唱，唱唱歌，想听什么，今天想听什么。"
    # ref_text = "Beside sands. Is that a fact? I'd love to capture a thunderbird!"
    # ref_text = "hey fucker,kick your ass,your suck!"

    ref_phones,_ = g2p(text_normalize(ref_text))
    # ref_phones = g2p(ref_text)

    ref_audio = torch.tensor([load_audio(input_audio, 48000)]).float()

    ref_seq = torch.LongTensor([cleaned_text_to_sequence(ref_phones)])

    # text_phones = g2p("音声合成のテストを行なっています。")
    # src_text = "嗯未来呢，我想继续忠实记录自己的生活,快乐的一只小跳蛙，当哩个当哩个当哩个当。"
    src_text = "快乐的一只小跳蛙，八百标兵奔北坡。"
    # src_text = "fee,town,long,,you mother fucker!!!holy shit,kick your asshole,stupid!"
    # src_text = "come on,light weight baby!!!"
    text_phones,_ = g2p(text_normalize(src_text))
    text_seq = torch.LongTensor([cleaned_text_to_sequence(text_phones)])

    # empty for ja or en
    ref_bert = torch.zeros((ref_seq.shape[1], 1024)).float()
    text_bert = torch.zeros((text_seq.shape[1], 1024)).float()

    ref_audio_16k = torchaudio.functional.resample(ref_audio,48000,16000).float()
    vits_hps_data_sampling_rate = 32000
    ref_audio_sr = torchaudio.functional.resample(ref_audio,48000,vits_hps_data_sampling_rate).float()

    zero_wav = np.zeros(
        int(vits_hps_data_sampling_rate * 0.3),
        dtype=np.float32,
    )
    wav16k, sr = librosa.load(input_audio, sr=16000)
    wav16k = torch.from_numpy(wav16k)
    zero_wav_torch = torch.from_numpy(zero_wav)
    wav16k = torch.cat([wav16k, zero_wav_torch]).unsqueeze(0)
    ref_audio_16k = wav16k

    ssl_content = ssl(ref_audio_16k).float()

    a = gpt_sovits(ref_seq, text_seq, ref_bert, text_bert, ref_audio_sr, ssl_content)
    soundfile.write("/Users/donkeyddddd/Documents/Rx_projects/git_projects/GPT_Sovits_cmdline/output_audio/onnx_without_EE_res.wav", a.cpu().detach().numpy(), vits_hps_data_sampling_rate)

if __name__ == "__main__":
    inference()
import os
import argparse
import soundfile as sf
import json

from infer_tool import TTSInference


def generate_audio(sovits_weights, 
                   gpt_weights, 
                   input_folder,
                   output_folder, 
                   ref_wav_path, 
                   prompt_text, 
                   prompt_language, 
                   text, 
                   text_language,
                   how_to_cut=None,
                   save=True
                   ):
    tts = TTSInference(sovits_weights=sovits_weights, gpt_weights=gpt_weights)
    
    infer_dict = {
        'ref_wav_path': os.path.join(input_folder, ref_wav_path),
        'prompt_text': prompt_text,
        'prompt_language': prompt_language,
        'text': text,
        'text_language': text_language,
        'how_to_cut': how_to_cut
    }

    audio_generator = tts.infer(**infer_dict)
    
    sr, audio = next(audio_generator)
    
    if save:
        ref_wav_name = ''.join(os.path.basename(ref_wav_path).split('.')[:-1])
        output_path = os.path.join(output_folder, f"{ref_wav_name}_{text[:6]}.wav")
        sf.write(output_path, audio, sr)
        print(f"Audio saved to {output_path}")
    else:
        return sr, audio
    

def process_batch(sovits_weights, gpt_weights, input_folder, output_folder, parameters_file):
    _, file_extension = os.path.splitext(parameters_file)
    
    if file_extension.lower() == '.json':
        with open(parameters_file, 'r', encoding='utf-8') as file:
            parameters = json.load(file)
            for param in parameters:
                generate_audio(sovits_weights, 
                               gpt_weights, 
                               input_folder,
                               output_folder,
                               param['ref_wav_path'], 
                               param['prompt_text'],
                               param['prompt_language'], 
                               param['text'],
                               param['text_language'],
                               param['how_to_cut']
                               )
    elif file_extension.lower() == '.txt':
        with open(parameters_file, 'r', encoding='utf-8') as file:
            for line in file:
                ref_wav_path, prompt_text, prompt_language, text, text_language, how_to_cut = line.strip().split('|')
                generate_audio(sovits_weights, 
                            gpt_weights, 
                            input_folder, 
                            output_folder, 
                            ref_wav_path, 
                            prompt_text, 
                            prompt_language, 
                            text, 
                            text_language, 
                            how_to_cut
                            )

def get_args_vscode_debug():
    parser = argparse.ArgumentParser(description="Batch Run TTS Inference")
    parser.add_argument("--sovits_weights", help="Path to sovits weights file",
                        default="SoVITS_weights/plasticfork1_e8_s72.pth")
    parser.add_argument("--gpt_weights", help="Path to gpt weights file",
                        default="GPT_weights/plasticfork1-e15.ckpt")
    parser.add_argument("--parameters_file", type=str, help="File containing parameters for batch processing",
                        default='inference_parameters_test.json')
        # parser.add_argument("--parameters_file", type=str, help="File containing parameters for batch processing",
                        # default='inference_parameters_test.txt')
    parser.add_argument("--input_folder", type=str, help="Folder of the input audio files",
                        default='/Users/donkeyddddd/Documents/Rx_projects/git_projects/GPT_Sovits_cmdline/input_audio')
    parser.add_argument("--output_folder", type=str, help="Folder to save the output audio files",
                        default='/Users/donkeyddddd/Documents/Rx_projects/git_projects/GPT_Sovits_cmdline/output_audio/')

    return parser.parse_args(args=[])


if __name__ == "__main__":
    # ============================
    # origin parser can used by inference.sh

    # parser = argparse.ArgumentParser(description="Batch Run TTS Inference")
    # parser.add_argument("--sovits_weights", required=True, help="Path to sovits weights file",
    #                     default="SoVITS_weights/plasticfork1_e8_s72.pth")
    # parser.add_argument("--gpt_weights", required=True, help="Path to gpt weights file",
    #                     default="GPT_weights/plasticfork1-e15.ckpt")
    # parser.add_argument("--parameters_file", type=str, help="File containing parameters for batch processing",
    #                     default='inference_parameters_test.txt')
    # parser.add_argument("--input_folder", type=str, help="Folder of the input audio files",
    #                     default='input_audio')
    # parser.add_argument("--output_folder", type=str, help="Folder to save the output audio files",
    #                     default='output_audio')
    # args = parser.parse_args()
    
    # ============================

    
    # ============================
    # vscode debug used
    args = get_args_vscode_debug()
    # ============================

    if not os.path.exists(args.output_folder):
        os.makedirs(args.output_folder)

    process_batch(args.sovits_weights, 
                  args.gpt_weights, 
                  args.input_folder, 
                  args.output_folder, 
                  args.parameters_file)

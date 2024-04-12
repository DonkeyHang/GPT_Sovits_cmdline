#!/bin/bash

# python src/inference/inference.py \
#  --sovits_weights pretrained_models/sovits_weights/saerman_cn/saerman_cn_e50_s350.pth \
#  --gpt_weights pretrained_models/gpt_weights/saerman_cn/saerman_cn-e50.ckpt \
#  --parameters_file inference_parameters.txt \
#  --output_folder output_audio/saerman_cn \

#  python src/inference/inference.py \
#  --sovits_weights pretrained_models/sovits_weights/dolly/dolly_e20_s140.pth \
#  --gpt_weights pretrained_models/gpt_weights/dolly/dolly-e25.ckpt \
#  --parameters_file inference_parameters.json \
#  --output_folder output_audio/dolly \

python src/inference/inference.py \
 --sovits_weights SoVITS_weights/plasticfork1_e8_s72.pth \
 --gpt_weights GPT_weights/plasticfork1-e15.ckpt \
 --parameters_file inference_parameters_test.txt \
 --output_folder output_audio/plasticfork \
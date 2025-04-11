import gradio as gr
import os
import json
import nbtlib
import updater
from numpy import array, int32, minimum
from structura_core import structura
import shutil
import threading
import time

debug = False
models = {}

def browse_struct(file):
    return file.name if file else ""

def update_models():
    with open("lookups/lookup_version.json") as file:
        version_data = json.load(file)
    updated = updater.update(version_data["update_url"], "Structura1-6", version_data["version"])
    return "更新完成！" + version_data["notes"] if updated else "目前已是最新版本"

def add_model(model_name, structure_file, x=0, y=0, z=0, opacity=100):
    """
    簡化版模型添加函式
    :param model_name: 模型名稱
    :param structure_file: 結構檔案路徑
    :param x/y/z: 偏移量 (預設0)
    :param opacity: 透明度 (0-100, 預設100)
    :return: 處理後的檔案路徑
    """
    file_path = structure_file.replace("\\", "/")
    
    return {
        "name": model_name,
        "offsets": [x, y, z],
        "opacity": (100 - opacity) / 100,
        "structure": file_path
    }

def delete_model(selected_model):
    if selected_model in models:
        del models[selected_model]
    return list(models.keys())


def run_conversion(pack_name, structure_file, x, y, z, opacity):
    """
    移植版轉換函式
    :return: 生成的資源包路徑
    """
    # 輸入驗證
    if os.path.isfile(f"{pack_name}.mcpack"):
        raise gr.Error("資源包已存在或名稱不能為空！")
    if not structure_file:
        raise gr.Error("請選擇結構檔案！")
    if not pack_name:
        raise gr.Error("請輸入資源包名稱！")

    # 處理檔案路徑
    if not isinstance(structure_file, str):
        structure_file = structure_file.name
    structure_path = os.path.abspath(structure_file.replace("\\", "/"))

    # 核心轉換邏輯
    structura_base = structura(pack_name)
    structura_base.set_opacity(opacity)
    
    structura_base.add_model("", structure_path)
    structura_base.set_model_offset("", [x, y, z])
    structura_base.generate_with_nametags()
    
    structura_base.make_nametag_block_lists()
    
    structura_base.compile_pack()
    
    # 處理輸出檔案
    mcpack_path, blocklist_path = process_output_files(pack_name)
    
    # 啟動清理線程
    threading.Thread(target=cleanup_specific_pack, args=(pack_name,), daemon=True).start()
    
    return (
        gr.File(value=mcpack_path),
        gr.File(value=blocklist_path) if blocklist_path else None
    )


def process_output_files(pack_name):
    """
    將輸出檔案從根目錄移動到 assets/pack_name/
    :return: (mcpack路徑, blocklist路徑)
    """
    # 確保目標目錄存在
    assets_dir = "assets"
    os.makedirs(assets_dir, exist_ok=True)
    target_dir = f"{assets_dir}/{pack_name}"
    os.makedirs(target_dir, exist_ok=True)
    
    # 處理 mcpack 檔案
    mcpack_src = f"{pack_name}.mcpack"
    mcpack_dst = f"{target_dir}/{pack_name}.mcpack"
    if os.path.exists(mcpack_src):
        shutil.move(mcpack_src, mcpack_dst)
    
    # 處理 blocklist 檔案
    blocklist_src = f"{pack_name}- block list.txt"
    blocklist_dst = f"{target_dir}/{pack_name}-block_list.txt"
    blocklist_path = None
    if os.path.exists(blocklist_src):
        shutil.move(blocklist_src, blocklist_dst)
        blocklist_path = blocklist_dst
    
    return mcpack_dst, blocklist_path

def cleanup_specific_pack(pack_name):
    """清理特定資源包的輸出檔案"""
    time.sleep(300)  # 5分鐘後清理
    target_dir = f"assets/{pack_name}"
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
        print(f"已自動清理資源包: {pack_name}")

with gr.Blocks(title="Structura") as demo:
    gr.Markdown("""
    ## Structura 資源包生成器 使用說明
    1. 上傳結構檔案(.mcstructure)
    2. 設定資源包名稱和參數
    3. 系統會自動生成:
       - 資源包(.mcpack)
       - 區塊列表(.txt)
    4. 系統5分鐘後自動清理舊檔案
    5. 按藍色箭頭可下載
    """)
    
    with gr.Row():
        gr.Markdown("## Structura 資源包生成器")
    
    with gr.Tab("單一模型"):
        with gr.Row():
            structure_file = gr.File(label="結構檔案", file_types=[".mcstructure"])
        pack_name = gr.Textbox(label="資源包名稱")
        
        with gr.Row():
            x = gr.Number(label="X偏移", value=0)
            y = gr.Number(label="Y偏移", value=0)
            z = gr.Number(label="Z偏移", value=0)
        
        opacity = gr.Slider(0, 100, label="透明度", value=100)
        
        convert_btn = gr.Button("轉換")
    
    output_mcpack = gr.File(label="輸出檔案")
    output_blocklist = gr.File(label="區塊列表")
    
    # 單一模型事件
    convert_btn.click(
        run_conversion,
        inputs=[pack_name, structure_file, x, y, z, opacity],
        outputs=[output_mcpack, output_blocklist]
    )

if __name__ == "__main__":
    demo.launch()

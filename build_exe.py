import os
import sys
import shutil
import subprocess
import glob
import re
from typing import Union

# 添加版本号常量
VERSION = "0.2-for-0.6.2~0.6.3"

def check_pyinstaller():
    """检查是否已安装PyInstaller，如果没有则自动安装"""
    try:
        import PyInstaller
        print("已检测到PyInstaller，继续打包...")
    except ImportError:
        print("未检测到PyInstaller，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("PyInstaller安装完成")

def check_dependencies():
    """检查其他依赖库是否安装，如果没有则自动安装"""
    dependencies = ["tomli", "packaging", "requests"]
    
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"已检测到{dep}库")
        except ImportError:
            print(f"未检测到{dep}库，正在安装...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
            print(f"{dep}库安装完成")

def check_files_exist():
    """检查必要文件是否存在"""
    files_to_check = [
        ("config_helper/config_helper.py", "配置助手主程序"),
    ]
    
    all_exist = True
    for file_path, desc in files_to_check:
        if not os.path.exists(file_path):
            print(f"错误：找不到{desc}文件：{file_path}")
            all_exist = False
    
    return all_exist

def build_exe():
    """打包config_helper为单独的exe文件"""
    print("开始打包config_helper...")
    
    # 检查必要文件是否存在
    if not check_files_exist():
        print("打包失败：缺少必要文件")
        return False
    
    # 创建临时目录
    if not os.path.exists("build_temp"):
        os.makedirs("build_temp")
    
    # 复制主脚本
    shutil.copy("config_helper/config_helper.py", "build_temp/")
    
    # 查找并复制所有 .md 文件
    md_files = glob.glob("config_helper/*.md")
    if not md_files:
        print("警告：在 config_helper 目录下未找到任何 .md 文件。")
    else:
        print(f"找到以下 .md 文件将打包：{', '.join(os.path.basename(f) for f in md_files)}")
        for md_file in md_files:
            shutil.copy(md_file, "build_temp/")
    
    # 创建main.py作为入口点
    with open("build_temp/main.py", "w", encoding="utf-8") as f:
        f.write("""
import os
import sys
import re
from typing import Union
from config_helper import EnvInfo, ConfigInfo, ConfigHelper, get_maibot_version

if __name__ == "__main__":
    # 将工作目录设置为可执行文件所在目录
    os.chdir(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd())
    
    print(f"======= MaiBot配置助手 v{VERSION} =======")
    print("该工具用于帮助检查和分析MaiBot配置文件")
    print("===============================")
    
    model_using = "deepseek-ai/DeepSeek-V3"
    env_info = EnvInfo(".env")
    result = env_info.check_env()
    if result == "not_set":
        print(env_info.error_message)
        input("按回车键退出...")
        exit()
    elif result == "only_ds":
        model_using = "deepseek-chat"
        print("你只设置了deepseek官方API，可能无法运行MaiBot，但是你仍旧可以运行这个帮助程序，请检查.env文件")
    elif result == "not_found":
        print(env_info.error_message)
        input("按回车键退出...")
        exit()
    
    # 获取 MaiBot 版本号 (假设 MaiBot-Core 在 exe 所在目录的上一级)
    # 注意：这个路径假设可能需要用户根据实际情况调整
    maibot_core_path = os.path.join("..", "MaiBot-Core") # 假设 MaiBot-Core 在上一级
    if not os.path.isdir(maibot_core_path):
        # 如果上一级没有，尝试当前目录 (如果用户把exe放到了 MaiBot-Core 同级)
         maibot_core_path = "."
         print(f"警告：未在 '../MaiBot-Core' 找到 MaiBot 核心目录，将尝试在当前目录查找 config.py")
         
    maibot_config_path = os.path.join(maibot_core_path, "src", "config", "config.py")
    maibot_version = get_maibot_version(maibot_config_path)
    if maibot_version:
        print(f"检测到 MaiBot 版本: {maibot_version}")
    else:
        print("未检测到 MaiBot 版本，将使用默认配置提示。")

    config_path = "./config/bot_config.toml"
    config_info = ConfigInfo(config_path)
    print("开始检查config/bot_config.toml文件...")
    result = config_info.check_bot_config()
    print(config_info)
    
    # 创建 ConfigHelper 时传入版本号
    helper = ConfigHelper(config_info, model_using, env_info, maibot_version=maibot_version)
    
    # 调用 load_config_notice() 来加载，它会处理版本
    helper.load_config_notice() 
    
    # 如果配置文件读取成功，展示如何获取字段
    if config_info.config_content:
        print("\\n配置文件读取成功，可以访问任意字段：")
        # 获取机器人昵称
        nickname = config_info.get_value("bot.nickname")
        print(f"机器人昵称: {nickname}")
        
        # 获取QQ号
        qq = config_info.get_value("bot.qq")
        print(f"机器人QQ: {qq}")
        
        # 获取群聊配置
        groups = config_info.get_section("groups")
        print(f"允许聊天的群: {groups.get('talk_allowed', [])}")
        
        # 获取模型信息
        models = config_info.get_all_models()
        print("\\n模型配置信息:")
        for model_name, model_info in models.items():
            provider = model_info.get("provider", "未知")
            model_path = model_info.get("name", "未知")
            print(f"  - {model_name}: {model_path} (提供商: {provider})")
        
        # 检查某字段是否存在
        if config_info.has_field("model.llm_normal.temp"):
            temp = config_info.get_value("model.llm_normal.temp")
            print(f"\\n回复模型温度: {temp}")
        else:
            print("\\n回复模型温度未设置")
            
        # 获取心流相关设置
        if config_info.has_field("heartflow"):
            heartflow = config_info.get_section("heartflow")
            print(f"\\n心流更新间隔: {heartflow.get('heart_flow_update_interval')}秒")
            print(f"子心流更新间隔: {heartflow.get('sub_heart_flow_update_interval')}秒")
            
    if result == "critical_error":
        print("配置文件存在严重错误，建议重新下载MaiBot")
        input("按回车键退出...")
        exit()
    elif result == "format_error":
        print("配置文件格式错误，正在进行检查...")
        error_message = config_info.error_message
        config_content_txt = config_info.config_content_txt
        helper.deal_format_error(error_message, config_content_txt)
    else:
        print("配置文件格式检查完成，没有发现问题")
        
    while True:
        question = input("\\n请输入你遇到的问题，麦麦会帮助你分析(输入exit退出)：")
        if question.lower() == "exit":
            break
        else:
            print("麦麦正在为你分析...")
            helper.deal_question(question)
    
    print("\\n程序结束，感谢使用MaiBot配置助手！")
    input("按回车键退出...")
""".replace("{VERSION}", VERSION))
    
    # 为所有找到的 .md 文件生成 --add-data 参数
    add_data_options = []
    separator = ';' if os.name == 'nt' else ':'
    for md_file in md_files:
        base_name = os.path.basename(md_file)
        add_data_options.extend(["--add-data", f"build_temp/{base_name}{separator}."])
    
    # 输出文件名包含版本号
    output_name = f"麦麦帮助配置-{VERSION}"
    
    # 开始打包
    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile",
        "--name", output_name,
        *add_data_options,
        "--clean",
        "--console",
        "build_temp/main.py"
    ]
    
    print("PyInstaller 命令:", ' '.join(pyinstaller_cmd))
    
    try:
        subprocess.check_call(pyinstaller_cmd)
        print(f"打包完成，可执行文件位于 dist/{output_name}.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"打包失败: {e}")
        print("请确保PyInstaller正确安装并尝试手动运行打包命令")
        return False
    finally:
        # 清理临时目录
        print("清理临时文件...")
        shutil.rmtree("build_temp", ignore_errors=True)

if __name__ == "__main__":
    print(f"开始打包MaiBot配置助手 v{VERSION}...")
    print("开始检查依赖...")
    check_dependencies()
    check_pyinstaller()
    success = build_exe()
    
    if success:
        print("打包过程成功完成！")
    else:
        print("打包过程未成功完成，请查看上面的错误信息")
    
    input("按回车键退出...") 
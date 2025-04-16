import os
import sys
import shutil
import subprocess

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
        ("config_helper/config_notice.md", "配置提示文件")
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
    
    # 复制需要的文件到临时目录
    shutil.copy("config_helper/config_helper.py", "build_temp/")
    shutil.copy("config_helper/config_notice.md", "build_temp/")
    
    # 创建main.py作为入口点
    with open("build_temp/main.py", "w", encoding="utf-8") as f:
        f.write("""
import os
import sys
from config_helper import EnvInfo, ConfigInfo, ConfigHelper

def get_resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        # 如果是打包后的可执行文件，使用_MEIPASS目录
        base_path = sys._MEIPASS
    else:
        # 否则使用当前目录
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)

if __name__ == "__main__":
    # 将工作目录设置为可执行文件所在目录
    os.chdir(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd())
    
    print("======= MaiBot配置助手 =======")
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
    
    config_path = "./config/bot_config.toml"
    config_info = ConfigInfo(config_path)
    print("开始检查config/bot_config.toml文件...")
    result = config_info.check_bot_config()
    print(config_info)
    
    helper = ConfigHelper(config_info, model_using, env_info)
    
    # 加载配置提示，确保路径正确
    try:
        notice_path = get_resource_path("config_notice.md")
        with open(notice_path, "r", encoding="utf-8") as f:
            helper.config_notice = f.read()
    except Exception as e:
        print(f"加载配置提示时出错: {str(e)}")
        helper.config_notice = "无法加载配置提示文件"
    
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
""")
    
    # 根据操作系统修改路径分隔符
    add_data_option = "build_temp/config_notice.md;." if os.name == 'nt' else "build_temp/config_notice.md:."
    
    # 开始打包
    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile",  # 打包成单个文件
        "--name", "MaiHelperConfig",  # 输出文件名
        f"--add-data={add_data_option}",  # 添加配置提示文件
        "--clean",  # 清理临时文件
        "--console",  # 显示控制台窗口
        "build_temp/main.py"  # 入口脚本
    ]
    
    try:
        subprocess.check_call(pyinstaller_cmd)
        print("打包完成，可执行文件位于 dist/MaiHelperConfig.exe")
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
    print("开始打包MaiBot配置助手...")
    print("开始检查依赖...")
    check_dependencies()
    check_pyinstaller()
    success = build_exe()
    
    if success:
        print("打包过程成功完成！")
    else:
        print("打包过程未成功完成，请查看上面的错误信息")
    
    input("按回车键退出...") 
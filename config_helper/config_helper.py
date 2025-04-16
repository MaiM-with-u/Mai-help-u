import os
import tomli
from packaging.version import Version

import time
from typing import Generator

import requests
import json

       
class EnvInfo:
    def __init__(self, env_path):
        self.env_path = env_path
        self.env_content_txt = None
        self.env_content = {}
        self.error_message = None
        

    def check_env(self):
        # 检查根目录是否存在.env文件
        if not os.path.exists(self.env_path):
            self.error_message = "根目录没有.env文件，请自己创建或者运行一次MaiBot\n你可以直接复制template/template.env文件到根目录并重命名为.env"
            return "not_found"
        
        #加载整个.env文件
        with open(self.env_path, "r", encoding="utf-8") as f:
            self.env_content_txt = f.read()
        
        #逐行读取所有配置项
        for line in self.env_content_txt.splitlines():
            if line.strip() == "":
                continue
            if "=" not in line:
                continue  # 跳过没有等号的行
            key, value = line.split("=", 1)
            self.env_content[key.strip()] = value.strip()
        
        # 检查.env文件的SILICONFLOW_KEY和SILICONFLOW_BASE_URL是否为空
        if "SILICONFLOW_KEY" not in self.env_content or "SILICONFLOW_BASE_URL" not in self.env_content:
            if "DEEP_SEEK_BASE_URL" not in self.env_content or "DEEP_SEEK_KEY" not in self.env_content:
                self.error_message = "没有设置可用的API和密钥，请检查.env文件，起码配置一个API来让帮助程序工作"
                return "not_set"
            else:
                self.error_message = "你只设置了deepseek官方API，可能无法运行MaiBot，请检查.env文件"
                return "only_ds"
        
        return "success"

class LLM_request_off:
    def __init__(self, model_name="deepseek-ai/DeepSeek-V3", env_info: EnvInfo = None, **kwargs):
        self.model_name = model_name
        self.params = kwargs
        if model_name == "deepseek-ai/DeepSeek-V3" or model_name == "Pro/deepseek-ai/DeepSeek-V3":
            self.api_key = env_info.env_content["SILICONFLOW_KEY"]
            self.base_url = env_info.env_content["SILICONFLOW_BASE_URL"]
        elif model_name == "deepseek-chat":
            self.api_key = env_info.env_content["DEEP_SEEK_KEY"]
            self.base_url = env_info.env_content["DEEP_SEEK_BASE_URL"]
        # logger.info(f"API URL: {self.base_url}")  # 使用 logger 记录 base_url

    def generate_stream(self, prompt: str) -> Generator[str, None, None]:
        """流式生成模型响应"""
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        # 构建请求体，启用流式输出
        data = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4,
            "stream": True,
            **self.params,
        }

        # 发送请求到完整的 chat/completions 端点
        api_url = f"{self.base_url.rstrip('/')}/chat/completions"
        print(f"Stream Request URL: {api_url}")

        max_retries = 3
        base_wait_time = 15

        for retry in range(max_retries):
            try:
                response = requests.post(api_url, headers=headers, json=data, stream=True)
                
                if response.status_code == 429:
                    wait_time = base_wait_time * (2**retry)
                    print(f"遇到请求限制(429)，等待{wait_time}秒后重试...")
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()

                # 处理流式响应
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: ') and not line.startswith('data: [DONE]'):
                            json_str = line[6:]  # 去掉 "data: " 前缀
                            try:
                                chunk_data = json.loads(json_str)
                                if (
                                    "choices" in chunk_data
                                    and len(chunk_data["choices"]) > 0
                                    and "delta" in chunk_data["choices"][0]
                                    and "content" in chunk_data["choices"][0]["delta"]
                                ):
                                    content = chunk_data["choices"][0]["delta"]["content"]
                                    yield content
                            except json.JSONDecodeError:
                                print(f"无法解析JSON: {json_str}")
                return

            except Exception as e:
                if retry < max_retries - 1:
                    wait_time = base_wait_time * (2**retry)
                    print(f"[流式回复]请求失败，等待{wait_time}秒后重试... 错误: {str(e)}")
                    time.sleep(wait_time)
                else:
                    print(f"流式请求失败: {str(e)}")
                    yield f"流式请求失败: {str(e)}"
                    return

        print("达到最大重试次数，流式请求仍然失败")
        yield "达到最大重试次数，流式请求仍然失败"

class ConfigInfo:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config_content = ""
        self.config_content_txt = None
        self.template_content = None
        self.version = None
        self.error_message = None
        
    def check_bot_config(self):
        """
        检查config/bot_config.toml文件中是否有缺失项目
        """

        if not os.path.exists(self.config_path):
            self.error_message = f"错误：找不到配置文件 {self.config_path}"
            return "not found"
        
        # 读取配置文件，先去掉注释，再解析TOML
        try:
            # 首先读取原始文件内容
            with open(self.config_path, "r", encoding="utf-8", errors="replace") as f:
                file_content = f.read()
                
            # 去掉注释并保留有效内容
            cleaned_lines = []
            for line in file_content.splitlines():
                # 去掉行内注释
                if "#" in line:
                    line = line.split("#")[0].rstrip()
                
                # 如果行不是空的且不是以#开头的注释行，则添加到cleaned_lines
                if line.strip() and not line.strip().startswith("#"):
                    cleaned_lines.append(line)
            
            # 将处理后的内容用于解析TOML
            self.config_content_txt = "\n".join(cleaned_lines)
            
            # 使用tomli解析处理后的内容
            self.config_content = tomli.loads(self.config_content_txt)
        except tomli.TOMLDecodeError as e:
            self.error_message = f"错误：配置文件格式错误：{e}"
            # 配置内容已经在上面设置了，不需要再次读取
            return "format_error"
        except UnicodeDecodeError as e:
            self.error_message = f"错误：配置文件编码错误，请使用UTF-8编码：{e}"
            return "format_error"
        
        # 读取模板配置文件
        template_path = "template/bot_config_template.toml"
        if not os.path.exists(template_path):
            self.error_message = f"错误：找不到模板配置文件，请检查你是否启动过或者该程序是否位于根目录 {template_path}"
            return "critical_error"
            
        try:
            with open(template_path, "rb") as f:
                template_content = tomli.load(f)
        except Exception as e:
            self.error_message = f"错误：无法解析模板配置文件，文件损坏，建议重新下载MaiBot：{e}"
            return "critical_error"
        
        # 获取版本信息
        inner_version = self.config_content.get("inner", {}).get("version")
        if not inner_version:
            self.error_message = "错误：配置文件中缺少版本信息"
            return "critical_error"
        
        try:
            self.version = Version(inner_version)
        except:
            self.error_message = f"错误：版本号格式错误：{inner_version}"
            return "critical_error"
        
        
        # 检查所有必需的顶级配置项
        required_sections = [
            "bot", "groups", "personality", "identity", "platforms", 
            "response", "message", "willing", "emoji", "memory", 
            "mood", "model"
        ]
        
        missing_sections = []
        for section in required_sections:
            if section not in self.config_content:
                missing_sections.append(section)
        
        if missing_sections:
            self.error_message = f"错误：配置文件缺少以下顶级配置项：{', '.join(missing_sections)}"
            return "critical_error"
        
        # 检查各个配置项内的必需字段
        missing_fields = []
        
        # 检查bot配置
        if "bot" in self.config_content:
            bot_config = self.config_content["bot"]
            if "qq" not in bot_config:
                missing_fields.append("bot.qq")
            if "nickname" not in bot_config:
                missing_fields.append("bot.nickname")
        
        # 检查groups配置
        if "groups" in self.config_content:
            groups_config = self.config_content["groups"]
            if "talk_allowed" not in groups_config:
                missing_fields.append("groups.talk_allowed")
        
        # 检查platforms配置
        if "platforms" in self.config_content:
            platforms_config = self.config_content["platforms"]
            if not platforms_config or not isinstance(platforms_config, dict) or len(platforms_config) == 0:
                missing_fields.append("platforms.(至少一个平台)")
        
        # 检查模型配置
        if "model" in self.config_content:
            model_config = self.config_content["model"]
            required_models = [
                "llm_reasoning", "llm_normal", "llm_topic_judge", 
                "llm_summary_by_topic", "llm_emotion_judge", "embedding", "vlm"
            ]
            
            for model in required_models:
                if model not in model_config:
                    missing_fields.append(f"model.{model}")
                elif model in model_config:
                    model_item = model_config[model]
                    if "name" not in model_item:
                        missing_fields.append(f"model.{model}.name")
                    if "provider" not in model_item:
                        missing_fields.append(f"model.{model}.provider")
        
        # 基于模板检查其它必需字段
        def check_section(template_section, user_section, prefix):
            if not isinstance(template_section, dict) or not isinstance(user_section, dict):
                return
            
            for key, value in template_section.items():
                # 跳过注释和数组类型的配置项
                if key.startswith("#") or isinstance(value, list):
                    continue
                    
                if key not in user_section:
                    missing_fields.append(f"{prefix}.{key}")
                elif isinstance(value, dict) and key in user_section:
                    # 递归检查嵌套配置项
                    check_section(value, user_section[key], f"{prefix}.{key}")
        
        for section in required_sections:
            if section in template_content and section in self.config_content:
                check_section(template_content[section], self.config_content[section], section)
        
        # 输出结果
        if missing_fields:
            print(f"发现 {len(missing_fields)} 个缺失的配置项：")
            for field in missing_fields:
                print(f"  - {field}")
        else:
            print("检查完成，没有发现缺失的必要配置项。")
    
    def get_value(self, path):
        """
        获取配置文件中指定路径的值
        参数:
            path: 以点分隔的路径，例如 "bot.qq" 或 "model.llm_normal.name"
        返回:
            找到的值，如果路径不存在则返回None
        """
        if not self.config_content:
            return None
            
        parts = path.split('.')
        current = self.config_content
        
        try:
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
            return current
        except:
            return None
    
    def has_field(self, path):
        """
        检查配置文件中是否存在指定路径
        参数:
            path: 以点分隔的路径，例如 "bot.qq" 或 "model.llm_normal.name"
        返回:
            布尔值，表示路径是否存在
        """
        return self.get_value(path) is not None
        
    def get_section(self, section_name):
        """
        获取配置文件中的整个部分
        参数:
            section_name: 部分名称，例如 "bot" 或 "model"
        返回:
            字典形式的部分内容，如果部分不存在则返回空字典
        """
        if not self.config_content:
            return {}
            
        return self.config_content.get(section_name, {})
        
    def get_all_models(self):
        """
        获取配置中所有的模型配置
        返回:
            包含所有模型配置的字典
        """
        if not self.config_content or "model" not in self.config_content:
            return {}
            
        return self.config_content.get("model", {})
        
    def __str__(self):
        return f"配置文件路径：{self.config_path}\n配置文件版本：{self.version}\n错误信息：{self.error_message}"

class ConfigHelper:
    def __init__(self, config_info: ConfigInfo, model_using = "", env_info: EnvInfo = None):
        self.config_info = config_info
        self.config_notice = None
        self.helper_model = LLM_request_off(model_name=model_using,env_info=env_info)
    
    def deal_format_error(self, error_message, config_content_txt):
        prompt = f"""
        这里有一份配置文件存在格式错误，请检查配置文件为什么会出现该错误以及建议如何修改，不要使用markdown格式
        错误信息：{error_message}
        配置文件内容：{config_content_txt}
        请根据错误信息和配置文件内容，用通俗易懂，简短的语言给出修改建议：
        """
        
        try:
            # 使用流式输出获取分析结果
            print("\n===== 麦麦分析结果 =====")
            for chunk in self.helper_model.generate_stream(prompt):
                print(chunk, end="", flush=True)
            print("\n=====================")
            
        except Exception as e:
            print(f"请求麦麦分析时出错: {str(e)}")
            print("请手动检查配置文件格式错误：", error_message)
    
    def load_config_notice(self):
        with open(os.path.join(os.path.dirname(__file__), "config_notice.md"), "r", encoding="utf-8") as f:
            self.config_notice = f.read()
    
    def deal_question(self, question):
        prompt = f"""
        这里有一份配置文件，请根据问题给出回答
        配置文件内容：{self.config_info.config_content_txt}
        关于配置文件的说明:{self.config_notice}
        问题：{question}
        """
        
        try:
            # 使用流式输出获取分析结果
            print("\n===== 麦麦分析结果 =====")
            for chunk in self.helper_model.generate_stream(prompt):
                print(chunk, end="", flush=True)
            print("\n=====================")
            
        except Exception as e:
            print(f"请求麦麦分析时出错: {str(e)}")
 
        

if __name__ == "__main__":
    model_using = "deepseek-ai/DeepSeek-V3"
    # model_using = "Pro/deepseek-ai/DeepSeek-V3"
    env_info = EnvInfo(".env")
    result = env_info.check_env()
    if result == "not_set":
        print(env_info.error_message)
        exit()
    elif result == "only_ds":
        model_using = "deepseek-chat"
        print("你只设置了deepseek官方API，可能无法运行MaiBot，但是你仍旧可以运行这个帮助程序，请检查.env文件")
    elif result == "not_found":
        print(env_info.error_message)
        exit()
    
    config_path = "./config/bot_config.toml"
    config_info = ConfigInfo(config_path)
    print("开始检查config/bot_config.toml文件...")
    result = config_info.check_bot_config()
    print(config_info)
    
    helper = ConfigHelper(config_info, model_using, env_info)
    helper.load_config_notice()
    
    # 如果配置文件读取成功，展示如何获取字段
    if config_info.config_content:
        print("\n配置文件读取成功，可以访问任意字段：")
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
        print("\n模型配置信息:")
        for model_name, model_info in models.items():
            provider = model_info.get("provider", "未知")
            model_path = model_info.get("name", "未知")
            print(f"  - {model_name}: {model_path} (提供商: {provider})")
        
        # 检查某字段是否存在
        if config_info.has_field("model.llm_normal.temp"):
            temp = config_info.get_value("model.llm_normal.temp")
            print(f"\n回复模型温度: {temp}")
        else:
            print("\n回复模型温度未设置")
            
        # 获取心流相关设置
        if config_info.has_field("heartflow"):
            heartflow = config_info.get_section("heartflow")
            print(f"\n心流更新间隔: {heartflow.get('heart_flow_update_interval')}秒")
            print(f"子心流更新间隔: {heartflow.get('sub_heart_flow_update_interval')}秒")
            
    if result == "critical_error":
        print("配置文件存在严重错误，建议重新下载MaiBot")
        exit()
    elif result == "format_error":
        print("配置文件格式错误，正在进行检查...")
        error_message = config_info.error_message
        config_content_txt = config_info.config_content_txt
        helper.deal_format_error(error_message, config_content_txt)
    else:
        print("配置文件格式检查完成，没有发现问题")
        
    while True:
        question = input("请输入你遇到的问题，麦麦会帮助你分析(输入exit退出)：")
        if question == "exit":
            break
        else:
            print("麦麦正在为你分析...")
            helper.deal_question(question)


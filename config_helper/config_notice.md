1.Q:为什么我的bot叫他名字不回消息？
A:请检查qq和nickname字段是否正确填写
请将默认字段：
qq = 114514
nickname = "麦麦"
改为你自己的qq号和bot名称（需要与qq昵称相同）

2.Q:为什么我设置了昵称和qq号，还是不回消息？
A：你需要先检查你的适配器是否与麦麦成功建立了连接
然后检查：
当前群是否在 `talk_allowed` 白名单中
如果群在 `talk_frequency_down` 列表中发言频率会降低

3. Q:如何修改日程表的内容，或者关闭日程表？
A：日程表目前无法关闭
如果日程表生成的内容太过科幻或者疯癫，可以尝试调整日程表的温度或者修改日程表描述

4. Q: 为什么显示：ModuleNotFoundError: No module named 'loguru'或者'tomli'或者'nonebot'
A: 你的python环境有问题，没有正确安装环境依赖
也有可能你安装了，但是你没有正确启动这个虚拟环境

5. Q: 为什么显示回复过长或者分割消息过多，返回默认回复？
A: 在response_splitter中，修改这些值：
enable_response_splitter 是否启用回复分割器
response_max_length 回复允许的最大长度
response_max_sentence_num 回复允许的最大句子数

6. Q: PFC模式是什么?
A: 是一个开发中的特殊私聊模式，与心流和推理模式完全独立，且尚未完善，如果无法运行或者出现异常，请关闭该模式


检查项：
1. 如果启用了
response_mode = "heart_flow"模式，那么只会使用llm_normal主模型，如果回复时间过长，或者思考时间过长，可能是因为你使用了推理模型或者免费模型

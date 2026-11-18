# 本轮后处理修正记录

1. source preflight首次拒绝分析RUN_RECORD的说明性raw_result_location；已保留旧记录，改为真实原始8TB输入root并保留本地CPU镜像范围，V1 preflight通过。
2. Root调用wrapper误读CONFIG.cwd，在启动分析前失败；原冻结字段是working_directory。已保留OPERATOR_WRAPPER_ATTEMPT0，神经/分析调用均为0。
3. 首次真实f29重算因错误的GPU drain晚于CPU service-end断言失败，记录完整保留；另建分析V2修正时间窗约束，原80格不重跑、不筛选。
4. publication helper的require-complete分支使用chosen同名局部变量覆盖文件集合；仅operator修正为index_path，之后完整80格有界清单门通过。

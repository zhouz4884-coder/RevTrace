# 首轮Linux CPU门：stdin/spawn操作器失败（无神经执行）

新runtime已干净冻结为`9492d3f9cb35e2b2849ec020817750a221248f0e`、完整59文件manifest `e9fc8b78…`，本地249个控制通过（1个完整Linux作者包测试仅在本地跳过）。正式远端源、作者BBB、26模型完整SHA、数据及环境前门完成后，CPU suite中的真实spawn子进程试验失败：测试主入口由`python -B -`从stdin运行，子进程试图重新导入`/home/user/<stdin>`，因此FileNotFoundError。

这是测试操作器入口缺陷，不是完整状态资格假设、神经数值或模型机制失败。首次stdout/stderr与B盘`runtime_cpu_v1`的失败gate/log保留；未启动任何新神经模型或服务格。

修复仅将测试入口换为B盘真实文件及if-main guard，并记录其完整bytes/SHA。第二次使用独立r2输出目录，以相同59文件源码、相同6格计划和数据/环境重新运行全部CPU，不跳过失败控制，不修改原C/U或任何期限。只有真实全套零skip门通过后才开始神经pilot。

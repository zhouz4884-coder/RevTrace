# 给导师看的当前校核稿

请转发 `RevTrace_DSN2027_Mentor_Review.pdf`。12页：11页正文＋1页参考文献；35条引用；摘要145词。配套源包为 `RevTrace_DSN2027_Mentor_Review_Source.zip`。

保留v27的新图4、第二幕、三见证论点和三条Lessons。校核只修正事实归属和因果关系：Ready-only的9次迟到拒绝单列；fencing对应输入资格、SUP对应视图支持；串行下一调用等待Owner的selected parent，慢调用连续发生时延迟累积；after-durable故障点是同步后、安装前，17–18秒差异的97.5%–98.2%定位到替换进程启动。首次信用与后续缺口改为并存关系。

没有改实验数值、模型、策略或投稿主线，没有新增GPU实验。原v27 PDF及40文件源包均保留原字节；校核源包使用规范文件名并去掉内部审阅文件及旧嵌套源包，23文件可独立编译。

## 标题讨论

当前保留 `RevTrace: Preserving Valid Progress across Trusted Feedback Revisions`，因为它同时交代系统、解决的对象与可信反馈修订场景。

`Timely Delivery Is Not Continued Availability` 很适合引言的论点和Lesson，作为单独标题会弱化系统和场景。若导师认为需要更强记忆点，可以考虑保留 `RevTrace:` 再强化后半句。改名本身不受所谓“冻结引用”阻碍，只需一致更新PDF、源包和匿名快照即可。本轮先不代替导师作这个选择。

## 已检查

无overfull或未定义引用；图4在第9页，与主表一致；48个点绑定当前80格；源包冷编译12页文字与渲染全部一致。实验数据与执行代码和此前已独立Linux检查通过的版本逐字节相同。

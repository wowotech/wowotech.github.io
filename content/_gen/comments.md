---
title: "全部评论"
url: "/comments/"
---

按时间倒序的最新 400 条评论（全站共 7962 条）。完整评论在各篇文章页底部，也可从[数据存档](/archive/)整体下载。

| 时间 | 评论者 | 评论 | 出处 |
| --- | --- | --- | --- |
| 2026-09-16 | 22 | @X1hq：你可以看下安卓的autosleep的实现，部分上层程序持wake_lock，然后以熄灭屏幕为检查点判断wake_lock是否全都释放，释放了就走内核休眠，也就是说上层程序也被分为了可以阻止休眠和不可以的两部分，内核不管上层在做什么任务，只要线程不是D状态就无法影响进入内核后的休眠 | [Linux电源管理(7)_Wakeup events f](/pm_subsystem/wakeup_events_framework.html#c9194) |
| 2026-09-02 | deng | @owen：ksoftirqd真正执行do_softirq的时候应该不会，抢占入口判断当前如果是中断上下文就不会执行切换 | [linux kernel的中断子系统之（八）：softi](/irq_subsystem/soft-irq.html#c9193) |
| 2026-09-02 | deng | @lingkep：如果硬中断打断的是软中断的执行，虽然硬中断退出了，但是仍然处在软中断上下文，文章可能是想表达这个吧 | [linux kernel的中断子系统之（八）：softi](/irq_subsystem/soft-irq.html#c9192) |
| 2026-06-29 | chaicai | 站内搜索不支持了么？ | [留言板](/message_board.html#c9191) |
| 2026-04-27 | 玖伍贰柒 | @坚强的小孩：3，虽然上面分析workqueue肯定会得到调用，但是关于是per workqueue和unbound workqueue哪一个性能好一点，这里确实不太清楚。
 -----------------------------------------------------
 你好，per cpu的wq有更好的… | [Concurrency Managed Workqueu](/irq_subsystem/alloc_workqueue.html#c9190) |
| 2026-04-27 | 玖伍贰柒 | @每天一小步：你好，讨论的这块代码的调用路径是这样的：
 alloc_and_link_pwqs
 	apply_workqueue_attrs
 		dfl_pwq = alloc_unbound_pwq(wq, new_attrs)
 		if (wq_calc_node_cpumask())
 			alloc_… | [Concurrency Managed Workqueu](/irq_subsystem/alloc_workqueue.html#c9189) |
| 2026-04-27 | 玖伍贰柒 | @bsp：你好。如果你的camera work是每次在irq handler里enqueue的话，我觉得可以固定让某个非cpu0来处理该irq，然后将workqueue改为BOUND类型，这样camera work每次都会由这个固定的非cpu0处理。
 /sys/devices/virtual/workqueue# e… | [Concurrency Managed Workqueu](/irq_subsystem/cmwq-intro.html#c9188) |
| 2026-04-27 | 玖伍贰柒 | @hdzhang：你好，关于max_active，我的理解是这样的：
 1. max_active是pool_workqueue的成员变量，表示当前pwq允许的最大acitve work数；
 2. 对于UNBOUND类型的workqueue，其对应的pool_workqueue不是per CPU的，而是per NUM… | [Concurrency Managed Workqueu](/irq_subsystem/cmwq-intro.html#c9187) |
| 2026-04-23 | rte | @三唑仑哪里有：发nm的广告,还尼玛是这种广告,冯死了 | [留言板](/message_board.html#c9186) |
| 2026-03-23 | biaowang | @manjaro-user：笔记本上的一般搭配了USB接口的蜂窝模块。首先怀疑是usb autosuspend有问题，唤醒后可能触发了usb reset | [留言板](/message_board.html#c9185) |
| 2026-03-09 | 凌云行者 | @gh：vmemmap只是加速了pfn和struct page之间的转换，整个sparse内存模型也不止是做了这个转换而已。比如vmemmap只映射真正存在的物理内存，kernel要知道哪一段地址真正有物理内存还是得依赖sparse内存模型的吧 | [Linux内存模型](/memory_management/memory_model.html#c9184) |
| 2026-03-06 | 凌云行者 | 有点串台了，TLB是在cpu上的东西，负责缓存虚拟地址映射物理地址的；TLB flush是invalidate这些cache。本文说的是内存中的dirty page更新到磁盘中 | [文件缓存回写简述](/memory_management/327.html#c9183) |
| 2026-03-05 | 凌云行者 | @Bob：把extfrag_threshold设置为1000只是说明kernel不会在分配内存时因为内存碎片程序进行compact了，不代表kernel不会compact，还有kcompactd线程负责compact | [linux kernel内存碎片防治技术](/memory_management/memory-fragment.html#c9182) |
| 2026-03-05 | 凌云行者 | @davidlamb：肯定是有的，所以选择在系统内存使用率低的时候进行碎片整合 | [linux kernel内存碎片防治技术](/memory_management/memory-fragment.html#c9181) |
| 2026-03-04 | 小石 | 讲的很好，谢谢 | [Linux kernel scatterlist API](/memory_management/scatterlist.html#c9180) |
| 2026-02-05 | bsp | @bsp：这就把每个cpu的tick_cpu_device的event_handler 赋成了hrtimer_interrupt。 | [Linux时间子系统之（十七）：ARM generic ](/timer_subsystem/armgeneraltimer.html#c9179) |
| 2026-02-05 | bsp | @yuhezhouping：cat /proc/timer_list ／grep event_handler
 一般Broadcast device 的 event_handler:  tick_handle_oneshot_broadcast  
 Per CPU device的event_handler:  hrt… | [Linux时间子系统之（十七）：ARM generic ](/timer_subsystem/armgeneraltimer.html#c9178) |
| 2026-01-27 | 菜就多练 | 虽然但是，这些地方要表达的是不是AV，而非VA...
 “当VMA和VA首次相遇”
 “立父子进程之间的VMA、VA的“大厦”，主要的步骤如下：”
 
 “建立子进程VMA和“父进程们”VA的关系”
 
 “建立子进程VMA和子进程VA的关系”
 
 “将该AVC加入VA红黑树”
 
 巨难受哇我去，我想了半天我寻思这… | [逆向映射的演进](/memory_management/reverse_mapping.html#c9177) |
| 2026-01-12 | 玖伍贰柒 | @wowo_man：TASKLET_STATE_SCHED标志 + 你说的pending位也是个solution，但我觉得当前的SCHED + RUN标志位方案更优雅，原因有二：
 1. tasklet的调度和执行是分开的，每个标志各司其职，逻辑更清晰；
 2. SCHED + RUN标志位只引入了一个变量state，… | [linux kernel的中断子系统之（九）：taskl](/irq_subsystem/tasklet.html#c9176) |
| 2026-01-12 | 玖伍贰柒 | @玖伍贰柒：是为了回复这个问题：
 schedule
 2015-07-07 17:33
 （b）中断返回software interrupt context，也就是中断抢占软中断上下文的场景
 =============================================
 楼主好，这句我有些疑问
 
 … | [linux kernel的中断子系统之（九）：taskl](/irq_subsystem/tasklet.html#c9175) |
| 2026-01-12 | 玖伍贰柒 | softirq那篇文章中，linuxer贴出了asmlinkage void __do_softirq(void)函数的代码，在开始处理软中断之前，调用了local_irq_enable()来打开本地中断响应。 | [linux kernel的中断子系统之（九）：taskl](/irq_subsystem/tasklet.html#c9174) |
| 2026-01-11 | 玖伍贰柒 | @linuxer_fy：ARM平台上，CPU收到中断后硬件会自动将CPSR寄存器的IRQ位置1，CPU将不会再响应中断，以此保证不会嵌套。对于其它CPU的场景，则由GIC保证，GIC对每个中断维护了一个状态机，当该中断处于active状态时，GIC不会把该中断再发给其它CPU。 | [linux kernel的中断子系统之（八）：softi](/irq_subsystem/soft-irq.html#c9173) |
| 2025-12-09 | lx | @owen：应该是的，大佬的中断子系统之（五）文章中写道：“在Linux kernel中，一个外设的中断处理被分成top half和bottom half，top half进行最关键，最基本的处理，而比较耗时的操作被放到bottom half（softirq、tasklet）中延迟执行。虽然bottom half被延迟… | [linux kernel的中断子系统之（八）：softi](/irq_subsystem/soft-irq.html#c9172) |
| 2025-10-14 | 牛逼666 | 牛逼 | [Linux kernel scatterlist API](/memory_management/scatterlist.html#c9171) |
| 2025-09-10 | hurricane618 | @wangxingxing：如果是arm32
 arch/arm/lib/xxxx.S 里面，比如set_bit在arch/arm/lib/setbit.S
 
 不同的架构会有所区别 | [Linux内核同步机制之（一）：原子操作](/kernel_synchronization/atomic.html#c9170) |
| 2025-08-26 | ppzzDD | wowo大佬，能否讲一讲关于蓝牙OTA那部。感谢感谢。 | [蓝牙协议分析(11)_BLE安全机制之SM](/bluetooth/le_security_manager.html#c9169) |
| 2025-08-22 | ppzzDD | 感谢wowo，2019年开始看wowo大佬的文章，2025年任来回味。 | [蓝牙协议分析(1)_基本概念](/bluetooth/bt_overview.html#c9168) |
| 2025-07-25 | test | 这个问题有意思，我感觉不是由dsb引起的， 因为这个时候 core A 收到这个tlbi还是能处理的。 
 看看是不是page fault的处理有其它依赖，造成时间很长。 h | [mmap在arm64背后的那个深坑](/linux_kenrel/516.html#c9167) |
| 2025-07-22 | magina | 这里描述的不对，当该值从memory中加载到cache 0中的cache line之后，该cache line的状态有以下几种情况：
 1. 如果其他Core的Cache没有缓存该Cache Line，那么Cache 0的状态为 E, 表示独占；
 2. 如果其他Core的Cache有缓存该Cache Line，那么C… | [Linux内核同步机制之（三）：memory barri](/kernel_synchronization/memory-barrier.html#c9166) |
| 2025-07-19 | Hichens | 常看常新 | [Linux设备模型(1)_基本概念](/device_model/13.html#c9165) |
| 2025-07-15 | pudding_art | @koala：cpu是逻辑核心，core是物理核心 | [Linux CPU core的电源管理(2)_cpu t](/pm_subsystem/cpu_topology.html#c9164) |
| 2025-07-13 | black8mamba | CONFIG_SPL_BUILD这个配置项应该在哪里配置打开呢。 | [u-boot启动流程分析(1)_平台相关部分](/u-boot/boot_flow_1.html#c9163) |
| 2025-07-12 | wpfly | 通过framebuffer来图形化的LVGL处在哪个位置呢？ | [Linux graphic subsytem(1)_概述](/graphic_subsystem/graphic_subsystem_overview.html#c9162) |
| 2025-07-09 | zouzp | @heziq：其实是把那个树状拓扑给横过来转换为链表 | [Linux电源管理(4)_Power Managemen](/pm_subsystem/pm_interface.html#c9161) |
| 2025-06-18 | xqplfly | @wangyongrui：芯片厂商或者固件厂商在固件阶段（一般是ATF）写进去的。 | [Linux时间子系统之（十七）：ARM generic ](/timer_subsystem/armgeneraltimer.html#c9160) |
| 2025-05-15 | 鲁班七号 | 2025年转行linux  考古来了。文章一看就懂了不少。点赞博主。 | [Linux设备模型(1)_基本概念](/device_model/13.html#c9159) |
| 2025-05-12 | wangyongrui | 设备树没写频率的情况下，寄存器CNTFRQ里的值是谁写进去的呢 | [Linux时间子系统之（十七）：ARM generic ](/timer_subsystem/armgeneraltimer.html#c9158) |
| 2025-04-26 | wangjing | 写得太好了 | [Linux时间子系统系列文章之目录](/timer_subsystem/time_subsystem_index.html#c9157) |
| 2025-04-26 | wangjing | 写得太好了！ | [Linux时间子系统系列文章之目录](/timer_subsystem/time_subsystem_index.html#c9156) |
| 2025-04-17 | DRAM | 圖面都沒辦法顯示出來好像掛點了。 | [DRAM 原理 2 ：DRAM Memory Organ](/basic_tech/309.html#c9155) |
| 2025-04-14 | Simbr | bus至少是不是还有个subsystem？ | [Linux设备模型(1)_基本概念](/device_model/13.html#c9154) |
| 2025-04-03 | troy | @testtest：只要ldrex-modify-strex中间插入了其它内核路径，该次的原子操作就会失败，也就是strex会失败，但atomic_add()里的汇编代码会对strex是否正确完成进行检查，如果是失败的，那么就会跳转到label 1处，再次进行ldrex-modify-strex。极端的说，如果每次ld… | [Linux内核同步机制之（一）：原子操作](/kernel_synchronization/atomic.html#c9152) |
| 2025-03-17 | gh | Linux 内核在 sparse 内存模型基础上实现了vmemmap 优化， vmemmap完全可以替换 sparse，为何还需要 sparse 存在？ | [Linux内存模型](/memory_management/memory_model.html#c9151) |
| 2025-02-28 | luc | keventd_wq 从2010 年就变成 system_wq 了 | [Concurrency Managed Workqueu](/irq_subsystem/workqueue.html#c9148) |
| 2025-02-28 | linux-fan | 一、前言 
 1、推迟到top half执行完毕 
  -> 这里typo,应该是bottom half? | [linux kernel的中断子系统之（九）：taskl](/irq_subsystem/tasklet.html#c9147) |
| 2025-02-27 | 内核菜鸟 | 感谢分享 | [支持与合作](/support_us.html#c9146) |
| 2025-02-25 | deven | @一个网友：从数据结构定义就能知道肯定不支持大页 | [Linux kernel scatterlist API](/memory_management/scatterlist.html#c9145) |
| 2025-02-17 | 内核小白 | @smcdef：今天正好看到这部分源码。KMALLOC_MAX_CACHE_SIZE 这个宏和架构有关，以及和你自己的config 有关。现在又有大页。总体上是16 14 12三个size, 4kb, 16kb, 64kb. | [图解slub](/memory_management/426.html#c9144) |
| 2025-02-17 | xinghuo | @1912：我也觉得是exclusive的，因为其他cache还不存在副本 | [Linux内核同步机制之（三）：memory barri](/kernel_synchronization/memory-barrier.html#c9143) |
| 2025-02-17 | xinghuo | “barrier只是保证compiler输出的汇编指令的顺序是OK的，不能确保CPU执行时候的乱序。 对这个问题的回答来自ARM architecture的内存访问模型：对于program order是A1-->A2的情况（A1和A2都是对Device或是Strongly-ordered的memory进行访问的指令），… | [Linux内核同步机制之（三）：memory barri](/kernel_synchronization/memory-barrier.html#c9142) |
| 2025-02-14 | xinghuo | @xinghuo：我想说的是ab赋值之间有没有屏障，与其之间有没有函数调用无关 | [编译乱序(Compiler Reordering)](/kernel_synchronization/453.html#c9140) |
| 2025-02-14 | xinghuo | 隐式编译器屏障(Implied Compiler Barriers)小节中，虽然最后的结论“要显式的插入barrier()，而不是依靠函数调用附加的隐式compiler barriers”大家都没有什么疑问，但个人对其中fun()函数不包含barrier()的情况下“大多数的函数调用都表现出compiler barri… | [编译乱序(Compiler Reordering)](/kernel_synchronization/453.html#c9139) |
| 2025-02-14 | xinghuo | 显式编译器屏障(Explicit Compiler Barriers)节中barrier()是最弱的屏障，只是静态的代码上做了屏障不能乱序，但后面对barrier()的解释中关联到缓存，寄存器这些硬件，是不是不太合适？ | [编译乱序(Compiler Reordering)](/kernel_synchronization/453.html#c9138) |
| 2025-02-13 | R_R | weight = 1024 / 1.25nice
 看起来不完全是根据这个公式计算得到的，大佬知道这些数值具体由来嘛 | [CFS调度器（1）-基本原理](/process_management/447.html#c9137) |
| 2025-02-07 | pdzhu | @ctwillson：state=4294967295为-1，退出idle态的意思 | [Linux cpuidle framework(4)_m](/pm_subsystem/cpuidle_menu_governor.html#c9136) |
| 2025-02-05 | linuxer | @白璐：有兴趣可以聊一聊，OPPO内核优化team需要的是对内核比较有热情的伙伴，而不是仅仅当成一份工作。
 我的微信号是：Linuxer-at-wowo | [Linux内核同步机制之（七）：RCU基础](/kernel_synchronization/rcu_fundamentals.html#c9134) |
| 2025-01-21 | ylsislove | 感谢大佬的文章 | [蓝牙协议分析(1)_基本概念](/bluetooth/bt_overview.html#c9133) |
| 2025-01-17 | xing | @王：牛逼 | [futex基础问答](/kernel_synchronization/futex.html#c9132) |
| 2025-01-14 | 白璐 | @linuxer：学长 还要人吗 | [Linux内核同步机制之（七）：RCU基础](/kernel_synchronization/rcu_fundamentals.html#c8951) |
| 2025-01-11 | muto | 终于看到更新了，赞 +1 | [mmap在arm64背后的那个深坑](/linux_kenrel/516.html#c8948) |
| 2024-12-26 | piter | 在linux 4.14 的版本中
 
 struct clk *__of_clk_get_from_provider(struct of_phandle_args *clkspec,
 				       const char *dev_id, const char *con_id)
 {
 	struct of_c… | [Linux common clock framework](/pm_subsystem/clock_framework_core.html#c8946) |
| 2024-12-17 | lingkep | 考古到了大佬的文章 看的好爽 另外有个疑问想请教下，在__irq_exit_rcu中判断if (!in_interrupt() && local_softirq_pending());invoke_softirq();之前会执行preempt_count_sub(HARDIRQ_OFFSET);那么既然中断不能嵌套，并… | [linux kernel的中断子系统之（八）：softi](/irq_subsystem/soft-irq.html#c8945) |
| 2024-12-05 | 毋庸置疑 | 看完了，感谢，，催更来了 | [蓝牙协议分析(11)_BLE安全机制之SM](/bluetooth/le_security_manager.html#c8944) |
| 2024-11-26 | rzbdz | 请教一下，为什么 __queue_work 中读取 wq->flags 的过程不需要对 wq->mutex 加锁呢？
 
 	if (unlikely(wq->flags & (__WQ_DESTROYING ／ __WQ_DRAINING) &&
 		     WARN_ON_ONCE(!is_chained_wo… | [Concurrency Managed Workqueu](/irq_subsystem/queue_and_handle_work.html#c8943) |
| 2024-11-25 | 水禾田 | 大神请教一下，mips架构，使用cpufreq框架动态调整CPU频率，发现调整频率后，时钟变了。比如900M调整到300M，发现sleep 1变成了3秒。Compare寄存器的1毫秒中断间隔一直是初始的900M的频率间隔(450000)。需要怎么调整才能使得时钟和CPU频率匹配呢？ | [Linux时间子系统之（二）：软件架构](/timer_subsystem/time-subsyste-architecture.html#c8942) |
| 2024-11-20 | zrant | 为什么调大cpu.cfs_period_us会有更大吞吐量。默认都是100ms这个是什么依据选的呢 | [CFS调度器（5）-带宽控制](/process_management/451.html#c8940) |
| 2024-10-14 | SuiTang | 请教下大神，蓝牙Beacon的Local Name可以重复吗？ | [蓝牙协议分析(3)_蓝牙低功耗(BLE)协议栈介绍](/bluetooth/ble_stack_overview.html#c8939) |
| 2024-10-14 | huozi | @testtest：下面 nothing 的提问中应该回答了你这个问题，进程切换的时候会重置monitor为open state：
 When an operating system performs a context switch, it must reset the local monitor to open s… | [Linux内核同步机制之（一）：原子操作](/kernel_synchronization/atomic.html#c8938) |
| 2024-10-14 | huozi | @passenger：是的，在ldrex后是会被打断，但返回原来的代码执行的时候，会执行失败，因为这时候monitor的状态是Open Access state，原来的代码继续执行后面的strex会执行失败，进而重新执行ldrex而保持原子性。 | [Linux内核同步机制之（一）：原子操作](/kernel_synchronization/atomic.html#c8937) |
| 2024-10-12 | hdzhang | CMWQ机制引入后我发现会有个问题，创建UNBOUND类型的workqueue指定的max_active是针对单个CPU的而不是系统全局的。
 假如系统有8个CPU core，我想限制workqueue总并发为64，那我就只能把max_active设置成8，但如果这样设置，我起一个进程把所有work入队，发现只有8个并… | [Concurrency Managed Workqueu](/irq_subsystem/cmwq-intro.html#c8936) |
| 2024-09-30 | 北葵依旧菜 | 感谢博主，博主多年前的文章在今天依旧熠熠生辉，解答了很多疑惑 | [关于蜗窝](/about.html#c8934) |
| 2024-09-27 | jqdeng | @新手：curr的确是从rb tree拿下来了，但是on_rq还是1，如果curr->on_rq=0,则说明curr即将进入睡眠或者迁移状态了，你可以去看一下__schedule中deactivate_task处的注释。 | [CFS调度器（2）-源码解析](/process_management/448.html#c8933) |
| 2024-09-12 | leelockhey | @入行真的好难：遇到写得好的技术博客真滴少啊，遇到写得好的一堆博客那是更稀有了 | [linux内核中的GPIO系统之（5）：gpio sub](/gpio_subsystem/pinctrl-and-gpio.html#c8932) |
| 2024-09-04 | 飞翔的蜗牛2024 | 请问怎么在head.S中bl __enable_mmu后使用串口打印进行调试？ | [ARM64的启动过程之（一）：内核第一个脚印](/armv8a_arch/arm64_initialize_1.html#c8928) |
| 2024-09-01 | Jam | 2024.9.1来考古 | [Linux设备模型(1)_基本概念](/device_model/13.html#c8927) |
| 2024-08-30 | Shiina | 一个电路（circuit）中，由于是回路，所以用电势差的概念会有问题
 因为回路首尾相连，电势从头处的高电势一直在下降，但是转一圈后，电势又突然从低电势跳到的高电势，如果用电势差来表示，那么这个回路的电势差为 0，这显示违反逻辑，所以我需要一个新概念来定义这种情况，这个概念就被称为电动势（electromotive f… | [基本电路概念之（一）：什么是电压？](/basic_subject/voltage.html#c8926) |
| 2024-08-30 | Shiina | 其中比较关键的点是相对位置概念和点电荷的静电势能计算。 | [基本电路概念之（一）：什么是电压？](/basic_subject/voltage.html#c8925) |
| 2024-08-30 | leelockhey | 你这是哪个内核版本 | [Linux电源管理(2)_Generic PM之基本概念](/pm_subsystem/generic_pm_architecture.html#c8924) |
| 2024-08-14 | ja | @dream：我看完這段也有相同的想法，引用 @dream 最後一段的說法
 
 即使当前进程在持有锁的时候，被高优先级进程抢占也访问了锁，进入自旋状态，那么内核不是支持时间片轮转的调度嘛，当产生 tick 中断的时候，高优先级的进程时间片用完，那么低优先级的进程就有再次执行的机会，只要低优先级有执行的机会，自然就能完… | [Linux内核同步机制之（四）：spin lock](/kernel_synchronization/spinlock.html#c8922) |
| 2024-08-08 | 元神高手 | 围观首席power managerment专家 | [Linux电源管理(14)_从设备驱动的角度看电源管理](/pm_subsystem/device_driver_pm.html#c8921) |
| 2024-08-08 | 十七 | 内核空间的映射在系统启动时就已经设定好，并且在所有进程的页表中这部分映射是相同的。 | [进程切换分析(1)：基本框架](/process_management/context-switch-arch.html#c8920) |
| 2024-08-02 | lw | sparse模型和disconti模型没看出来有什么本质区别啊 | [Linux内存模型](/memory_management/memory_model.html#c8919) |
| 2024-08-01 | 肥饶 | 一个没设置好就出错 | [mmap在arm64背后的那个深坑](/linux_kenrel/516.html#c8918) |
| 2024-07-31 | orange | 点赞点赞，对linuxer的文章总结到位 | [Device Tree（四）：文件结构解析](/device_model/dt-code-file-struct-parse.html#c8917) |
| 2024-07-22 | mubai | wowo您好，我们这边有个奇怪的现象，是概率性的，通过在bl31的代码里增加打印的方式，发下系统suspend的流程走到.cpu_kill的时候执行__invoke_psci_fn_smc后没有陷入到ATF中，想请教下会有哪方面的原因? | [Linux电源管理(6)_Generic PM之Susp](/pm_subsystem/suspend_and_resume.html#c8914) |
| 2024-07-14 | Aloys | 最新的Android版本已经不再通过/sys/power/wake_lock和/sys/power/wake_unlock来控制wake source了。
 当前通过SuspendControlService与/sys/power/wake_count来实现上层和kernel的锁同步 | [Linux电源管理(9)_wakelocks](/pm_subsystem/wakelocks.html#c8913) |
| 2024-07-14 | haohlliang | 赞!请教下，有什么工具可以扫出业务代码中低hit行为？ | [浅谈Cache Memory](/memory_management/458.html#c8912) |
| 2024-07-05 | 新手 | 圖面好像顯示不出來，請問有什麼方法可以看到圖示呢謝謝 | [DRAM 原理 1 ：DRAM Storage Cell](/basic_tech/307.html#c8911) |
| 2024-06-09 | shousi | 挺巧妙的 | [Linux reset framework](/pm_subsystem/reset_framework.html#c8906) |
| 2024-06-03 | kkkkkkkaixa | @风中尘埃：换块板子 | [《奔跑吧，Linux内核》已经上架预售了](/tech_discuss/running_kernel.html#c8904) |
| 2024-05-31 | 育 | @wowo 想請問大神，我的board有兩個Kernel 但只有其中一個可以輸入指令另一個不能，這樣我要怎麼輸入WFI command | [ARM WFI和WFE指令](/armv8a_arch/wfe_wfi.html#c8903) |
| 2024-05-26 | duckwu | @立志学linux：我觉得percpu变量就是等于定义了好几个不同的变量但是比定义多个变量更好。假设一个进程在运行过程中需要某个变量，该变量在各个CPU上逻辑独立，但是程序员在编码时是无法知道该进程运行在哪个cpu上，也就无法为其指定对应的变量。想反，让cpu自己去选择对应的变量即per-cpu变量就可以解决这个问题。 | [Linux内核同步机制之（二）：Per-CPU变量](/kernel_synchronization/per-cpu.html#c8902) |
| 2024-05-24 | 新手 | 請問為什麼Storage Capacitor 中儲存正電荷會流向Bitline 呢兩邊電壓不是都是VCC/2嗎 
 感謝。 | [DRAM 原理 1 ：DRAM Storage Cell](/basic_tech/307.html#c8901) |
| 2024-05-18 | 葡萄 | 原文中的“而一个AV会管理若干的VMA，所有相关的VMA（其子进程或者孙进程）都挂入红黑树，根节点就是AV的rb_root成员。”  应该是一个AV 会管理若干AVC, 这里描述有误 | [逆向映射的演进](/memory_management/reverse_mapping.html#c8900) |
| 2024-05-16 | jiyouzhan | 这篇文章写得深入浅出，让我这个小白也看懂了！ | [mmap在arm64背后的那个深坑](/linux_kenrel/516.html#c8899) |
| 2024-05-15 | er3s56 | 文中内容："而pym，则根据具体情况，具体实现。例如：要通过网络接口和终端设备交互，则pym需要打开对应的socket，将pts写来的数据，从socket送出，将从socket读取的数据，送回给pts。"
 这里的pym似乎是笔误，应为ptm。 | [Linux TTY framework(3)_从应用的角](/tty_framework/application_view.html#c8898) |
| 2024-05-05 | abcde | 我想“Linux菜鸟”的本意应该是 “当某个se的slice > sysctl_sched_min_granularity 
  && < tick”时，如果此se用完了自己的slice，但，中断时间却又尚未到达，那么，就没有机制让此se停下来，所以，se实际执行时间，不就超出自己应得的slice了吗？
 
 这个问题… | [CFS调度器（2）-源码解析](/process_management/448.html#c8897) |
| 2024-05-03 | abcde | 图中上半部，nr_runing和h_nr_running的值分别等于10和19，多出的9是group cfs_rq的h_nr_running。group cfs_rq由于没有group se，因此nr_runing和h_nr_running的值都等于9。
 ===============================… | [CFS调度器（3）-组调度](/process_management/449.html#c8896) |
| 2024-05-02 | elliot | @keith：有一个工具叫做pahole，可以解决你的问题 | [KASAN实现原理](/memory_management/424.html#c8895) |
| 2024-05-02 | elliot | @pete：KASAN目前已经支持vmalloc的检测了 | [KASAN实现原理](/memory_management/424.html#c8894) |
| 2024-04-25 | 卷心菜 | @zecard：这种情况kasan应该检测不出来 | [KASAN实现原理](/memory_management/424.html#c8890) |
| 2024-04-24 | 小明不明白 | 请问一个问题：
 如何控制win10的usb接口的供电？例如cmd命令，编写程序等方法。
 期望的结果就是能随时让电脑的某个usb接口断电，以及随时可以开启供电。
 感谢任何关注与回复！ | [留言板](/message_board.html#c8889) |
| 2024-04-24 | 安庆 | @markened-frank：是的，但是它前面是tlbi啊 | [mmap在arm64背后的那个深坑](/linux_kenrel/516.html#c8888) |
| 2024-04-23 | bngvcztboj | 劲舞团问道密传一条龙www.43vb.com1325876192@qq.com倚天2龙驹魔钥巨商服务端出售 
  
 丝路传说开区大话西游开区蜀门开区机战开区剑侠情缘开区
 绝对女神开区传说OL开区刀剑开区弹弹堂开区科洛斯开区
 魔力宝贝开区武林外传开区网页游戏开区页游开区希望OL开区
 成吉思汗开区剑侠世界开区全民奇… | [留言板](/message_board.html#c8887) |
| 2024-04-20 | small | wowo，你好
 我遇见有一个唤醒锁一直无法关闭，我想强制关闭这个唤醒锁，我应该怎样去调用接口强制关闭这个唤醒锁呢 | [Linux电源管理(8)_Wakeup count功能](/pm_subsystem/wakeup_count.html#c8886) |
| 2024-04-16 | 狗子 | @王：老铁 休息就别卷了 受不了 | [futex基础问答](/kernel_synchronization/futex.html#c8885) |
| 2024-04-12 | markened-frank | 我记得DSB的语义是等待本核的前面的操作完成，并不能等待其他核的操作完成吧 | [mmap在arm64背后的那个深坑](/linux_kenrel/516.html#c8884) |
| 2024-04-12 | bsp | @icy_river：bsp
 2023-02-01 13:11
 ticket-based-spinlock有个重大问题：
 假如当CPU0获取了spinlock，而CPU1、CPU2、CPU3...在等锁，在CPU0 spin_unlock时通过sev/stlr唤醒其它所有所有CPU去check是否轮到自己；我们通… | [Linux内核同步机制之（四）：spin lock](/kernel_synchronization/spinlock.html#c8883) |
| 2024-04-12 | bsp | @icy_river：嗯，我其实就在说qspinlock 替代ticket-based-spinlock的原因。
 通过qspinlock，只需要唤醒lock->next所在的cpu，其它cpu继续自旋。 | [Linux内核同步机制之（四）：spin lock](/kernel_synchronization/spinlock.html#c8882) |
| 2024-04-12 | bsp | @icy_river：嗯，我其实就在说qspinlock 替代ticket-based-spinlock的原因。
 通过qspinlock，只需要唤醒lock->next所在的cpu，其它cpu继续自旋。 | [Linux内核同步机制之（四）：spin lock](/kernel_synchronization/spinlock.html#c8881) |
| 2024-04-11 | aly | @see：cfs保证一个调度周期结束后所有进程的虚拟时间是一样的。
 
 调度周期内，不同进程会累积自己的虚拟时间，因此会有虚拟时间上的差别。 | [CFS调度器（1）-基本原理](/process_management/447.html#c8880) |
| 2024-04-02 | 透苇 | 终于看到更新了，赞 | [mmap在arm64背后的那个深坑](/linux_kenrel/516.html#c8879) |
| 2024-03-28 | huozi | @兔子：既然是reserve，那就应该可用可不用。开启了MMU之后，若要用，应该要建立映射通过虚拟地址来访问。 | [内存初始化（上）](/memory_management/mm-init-1.html#c8878) |
| 2024-03-28 | huozi | @HW.Yang：页表自身存放在哪里，原文中也有一些提示，如下：
 内核起始刚开始的汇编代码基本上是PIC的，首先需要定位到页表的位置，然后在页表中填入kernel image mapping和identity mapping的页表项。页表的起始位置比较好定（bss段之后），但是具体的size还是需要思考一下的。 | [内存初始化（上）](/memory_management/mm-init-1.html#c8877) |
| 2024-03-28 | huozi | @landau：我想原文应该也是想表达这样一个意思，举一个映射范围最大为2M的例子，只是他这个例子，我们读者可能都默认level0-level2对应的三个page均填满，那样映射范围肯定不止2M，原文level0-level2 均是只有一个entry才有原文的结论。 | [内存初始化（上）](/memory_management/mm-init-1.html#c8876) |
| 2024-03-28 | huozi | @啊啊啊：你这个前提就是entry0、entry1、entry2均是1，entry3为512才是这个，但为什么level 0、level 1、level 2、level 3均有1page保存，为什么entry0、entry1、entry2均是1，entry3为512呢？ | [内存初始化（上）](/memory_management/mm-init-1.html#c8875) |
| 2024-03-28 | huozi | 我也是还没看懂这句话，映射范围不应该是entry0*entry1*entry2*entry3*4k吗？
 另外entry3为何是512？ | [内存初始化（上）](/memory_management/mm-init-1.html#c8874) |
| 2024-03-27 | aly | @gzz：文章说的比较明白了，我理解你说的64号中断是硬件中断号。硬件中断号在级联情况下的确是会重复的，但驱动里用的是软件中断号，linux在启动时帮你映射好的。软件中断号不会重复，你可以在驱动代码里通过irq_of_parse_and_map或者platform_get_irq获取软件中断号 | [Linux kernel的中断子系统之（二）：IRQ D](/irq_subsystem/irq-domain.html#c8873) |
| 2024-03-18 | wiryls | 时隔多年无意间看到这篇文章，回想起前段时间也有想过类似的问题，忍不住来一记洛阳铲。
 
 我倒是认为基因并不独特，基因也只是一种信息的载体。复制的是信息，变异的是信息，传播的是信息，消亡的也是信息。基因携带的信息目前只能由某些细胞读写，人类暂时只能分析其中的一部分。如果人类彻底掌握了基因解析、修改的技术，说不定还能诞生… | [进化论、人工智能和外星人](/tech_discuss/toe_ai_et.html#c8872) |
| 2024-03-12 | linzai | 大佬你好，你在文中多次使用crash，但是crash是需要dump文件，你的dump文件是将云宿主机通过/proc/sys/sysrq-trigger直接生成的吗？ | [关于java单线程经常占用cpu100%分析](/linux_kenrel/483.html#c8871) |
| 2024-03-07 | cheng | 坚持更新，佩服 | [支持者列表](/support_list.html#c8870) |
| 2024-03-05 | rankie007 | 老师好，我们在KVM虚拟化开发过程中需要适配不同厂家的CPU，遇到个问题，当两家CPU的external clock（通过dmidecode -t processor查询）不同时，其上运行的虚拟机执行在线迁移后，虚拟机内部系统的计时器会加快或减慢，比如A厂商CPU的 external clock是100Mhz，B厂商C… | [Linux时间子系统之（十七）：ARM generic ](/timer_subsystem/armgeneraltimer.html#c8869) |
| 2024-02-29 | bsp | kernel是不建议使用浮点运算的，尝试回答一下：
 1.使用浮点寄存器是存在竞争的，此时需要保护这些register的，包括入栈&出栈；arm64有16个128bit的浮点寄存器：q0~q15，入栈/出栈的时间和内存消耗都不小；
 
 2.竞争点有：
   两个kernel-thread在同一个cpu-core上去访… | [Linux时间子系统之（十五）：clocksource](/timer_subsystem/clocksource.html#c8868) |
| 2024-02-23 | donge | @test：有道理 | [为什么会有文件系统(一)](/filesystem/370.html#c8867) |
| 2024-02-16 | btrace | @kangkang：你来个深入的，否则就shutup | [以太网驱动的流程浅析(二)-Ifconfig的详细代码流](/linux_kenrel/466.html#c8866) |
| 2024-02-07 | landau | @melo：基于melo 的说法，如果level0不止一个entry，那么意味着level1的entry不止一个page（此时一个page在level0~level3 中都是能保存512个entry），因为level0的entry存放的值，对应的是pgd table中的level1的table的地址。level1也同理… | [内存初始化（上）](/memory_management/mm-init-1.html#c8865) |
| 2024-01-25 | testtest | @wangdl：就是线程1的ldrex因为线程2先strex而失效，但在线程1strex之前，其他线程如果又ldrex一次，那么线程1下来的strex是不是还是有效的？ | [Linux内核同步机制之（一）：原子操作](/kernel_synchronization/atomic.html#c8864) |
| 2024-01-19 | Syed | @憨憨也是态度：十年之后终于来到了这里，感谢还在！感谢您的坚持！作为一名嵌入式驱动新手，我也会继续努力，一定会坚持下去的！ | [关于蜗窝](/about.html#c8863) |
| 2024-01-17 | lw | @wowo：逻辑层那些协议的具体使用场景，能帮忙列一下吗？ | [蓝牙协议分析(2)_协议架构](/bluetooth/bt_protocol_arch.html#c8862) |
| 2024-01-13 | Harry Song | 文中对 ticket 的机制进行举例和实际的汇编实现有偏差：
 
 "最开始的时候，slock被赋值为0，也就是说owner和next都是0，owner和next相等，表示unlocked。"
 
 --> 实际上应该是默认值是1，第一位来排队的，先 next+1 = 1,然后 当前owner == 当前next，拿到… | [Linux内核同步机制之（四）：spin lock](/kernel_synchronization/spinlock.html#c8861) |
| 2024-01-11 | slava_chen | @slava_chen：抱歉，我又看了sched_create_group()->alloc_fair_sched_group()->init_tg_cfs_entry()的代码，发现task_group的cfs_rq和se长度的确是CPU数目 | [CFS调度器（3）-组调度](/process_management/449.html#c8860) |
| 2024-01-11 | slava_chen | 我认为struct task_group里边的成员**se，他的长度和该主机中的CPU数量没有关系，成员**cfs_rq的长度和CPU数量数目相等。
 **se的长度只取决于当前task_group有多少个任务实体，每一个cfs_rq队列都同时可以接受多个任务实体se，但是一个cfs_rq队列只能对应于一个CPU上的r… | [CFS调度器（3）-组调度](/process_management/449.html#c8859) |
| 2024-01-09 | 灵药世家 | FM2 GHB DDK 唛可奈因可瑞敏微信sddf828
 听话水/乖乖水/催情/迷昏/迷幻/迷情药出售
 氟硝西泮蓝精灵,乙醚,春药,久光千岛片，微信SDDF828
 【迷昏药喷雾型800元】【迷昏药香烟型900元】【迷昏药服用型500元】【迷昏药拍肩型900元】【迷昏药盘香型900元】【迷情粉500元】【七氟烷12… | [留言板](/message_board.html#c8858) |
| 2024-01-08 | 憨憨也是态度 | 感谢 你的蓝牙笔记写的很好 我与梦想永远在路上 | [关于蜗窝](/about.html#c8857) |
| 2024-01-05 | 坚强的小孩 | @ele：以下是一些自己的看法，麻烦看看有什么不对的地方，希望大家指出来，谢谢。
 1、workqueue的调度其实还是依赖与进程调度吧，虽然是软中断触发的，但是调度还是进程的调度，所以不存在有大量的线程长时间占用，而调度不到workqueue的情况，只是workqueue会等待的时间比正常的时间长一点而已；
 2、大… | [Concurrency Managed Workqueu](/irq_subsystem/alloc_workqueue.html#c8856) |
| 2024-01-05 | semilog | 最近看你很久没有更新了，时光如梭，十年一晃而过，那个对技术充满激情的少年还在吗？对我们这些追求技术的人来说，永远是少年~~~ 你的文章写的很好。 | [关于蜗窝](/about.html#c8855) |
| 2023-12-25 | icy_river | // glibc实现
 int
 __getpriority (enum __priority_which which, id_t who)
 {
   int res;
 
   res = INLINE_SYSCALL (getpriority, 2, (int) which, who);
   if (res >… | [Linux调度器：用户空间接口](/process_management/scheduler-API.html#c8854) |
| 2023-12-25 | 遥遥领先 | 不快餐，怎么遥遥领先，怎么印钱，怎么炒房。不是技术人想快餐，而是顶层设计的是遥遥领先的规则 | [关于蜗窝](/about.html#c8853) |
| 2023-12-25 | russell | 23年几乎没有更新了，太可惜了 | [支持者列表](/support_list.html#c8852) |
| 2023-12-18 | エルメス 550 | 時計，バッグ，財布，ルイヴィトンコピー，エルメスコピー
 弊店に主要な販売する商品は時計，バッグ，財布，ルイヴィトンコピー，エルメスコピー，
 シャネルコピー，グッチコピー,プラダコピー,ロレックスコピー，カルティエコピー，オメガコピー，
 ウブロ コピーなどの世界にプランド商品です。
 2006年に弊社が設立された、… | [schedutil governor情景分析](/process_management/schedutil_governor.html#c8851) |
| 2023-12-09 | manjaro-user | 请教老大一个问题，我们在thinkpad的X1笔记本上安装了manjaro,6.1的内核，最近发现休眠后唤醒的时候，笔记本的LTE4宽带网络经常不能自动恢复，需要手动执行一下“systemctl restart ModemManager”，偶然也能唤醒后自动恢复联网，在网上查了一圈也没有头绪，想请教一下老大，能不能帮忙… | [留言板](/message_board.html#c8850) |
| 2023-12-06 | 坚强的小孩 | 写的真好，干货满满 | [RCU（2）- 使用方法](/kernel_synchronization/462.html#c8849) |
| 2023-11-14 | Enlin | 在4.15中，我觉得节点信息应该是：kaslr-seed = <0x10000000 0x10000000>;这类格式的。
 
 因为下面有如下的判断：
 if (!prop ／／ len != sizeof(u64))
 
 节点长度不够，直接return 0； | [KASLR](/memory_management/441.html#c8846) |
| 2023-11-08 | chenan | @schspa：我理解的 autosleep 本身就是给 Android 打的补丁，autosleep 在内核里本身也是一个配置项。
 对于 android 的休眠机制，完成由上层控制了，只要没唤醒锁，抓住机会就睡 | [Linux电源管理(10)_autosleep](/pm_subsystem/autosleep.html#c8845) |
| 2023-11-08 | 设备树工程师 | 为这种蜗牛精神干杯 | [关于蜗窝](/about.html#c8844) |
| 2023-11-06 | schspa | @chenan：autosleep只是android不使用吧, 内核里边的支持还是在的吧。 | [Linux电源管理(10)_autosleep](/pm_subsystem/autosleep.html#c8843) |
| 2023-11-02 | chenan | autosleep 早已经废弃了，蜗窝也好久没更新了 | [Linux电源管理(10)_autosleep](/pm_subsystem/autosleep.html#c8842) |
| 2023-11-01 | wasd | @marvin263：那请问，如果是这样的话，那按照nr_running * sysctl_sched_min_granularity算出来的调度周期不是不准确了吗？因为nice值小的进程会运行超过sysctl_sched_min_granularity | [CFS调度器（6）-总结](/process_management/452.html#c8841) |
| 2023-10-26 | bsp | @农夫山泉：linux的软中断（invoke_softirq） 是在硬中段（top half）退出时才会执行，关了hardirq就等于关了softirq。 | [linux kernel的中断子系统之（八）：softi](/irq_subsystem/soft-irq.html#c8840) |
| 2023-10-25 | chenningjun | @owen：不会，但softirqd内部 cond_resched 主动出让CPU了。
 按目前理解：调度抢占是针对用户态。内核态只有中断。 | [linux kernel的中断子系统之（八）：softi](/irq_subsystem/soft-irq.html#c8839) |
| 2023-10-23 | chenan | @myh123：android 9以后已经没有 libsuspend，取而代之的 SystemSuspend service | [Linux电源管理(10)_autosleep](/pm_subsystem/autosleep.html#c8838) |
| 2023-10-16 | 在努力 | 新手入门linux 看到你写的文章 点赞 继续点灯去了 哈哈哈 | [关于蜗窝](/about.html#c8837) |
| 2023-10-15 | xiaotonga | 驱动节点通过sysfs暴露给用户，通过sysfs可以查看驱动节点信息，打call | [致驱动工程师的一封信](/device_model/429.html#c8836) |
| 2023-10-10 | Sail | @jalen：设置上升沿触发或者下降沿触发就能达到只触发一次 | [留言板](/message_board.html#c8835) |
| 2023-10-06 | jalen | 请教各位大佬个问题：
    电平触发类型的中断（比如高电平触发），需要手动将电平恢复到低电平吗？如果不需要的话，怎么保证这个中断不会反复的触发呢？（个人理解，这种类型的中断，会保持触发电平，那么如果不恢复电平，退出中断后，不就立即又触发中断了吗？） | [留言板](/message_board.html#c8834) |
| 2023-10-01 | bngvpyhuyj | 天堂传世真封神服务端出售www.a3sf.com776356990@qq.com墨香决战千年希望OL服务端出售 
  
 丝路传说开区大话西游开区蜀门开区机战开区剑侠情缘开区
 绝对女神开区传说OL开区刀剑开区弹弹堂开区科洛斯开区
 魔力宝贝开区武林外传开区网页游戏开区页游开区希望OL开区
 成吉思汗开区剑侠世界开区全… | [留言板](/message_board.html#c8833) |
| 2023-09-28 | wangjb | 老板，你好！  
 我这里遇到一个dma 直接映射物理内存的问题，是用cma的机制，我发的时间太长了，都还没有 解决，能否帮忙提供思路，非常感谢！！！
  驱动qca-7850调试的结果和我写的关于A函数的内核测试模块的结果一样，我就用我的测试程序描述一下问题。
   问题1  
            linux 内… | [Linux DMA Engine framework(1](/linux_kenrel/dma_engine_overview.html#c8832) |
| 2023-09-25 | baron | 还能留言 | [Linux电源管理(1)_整体架构](/pm_subsystem/pm_architecture.html#c8831) |
| 2023-09-21 | wwlinus | 实际电路中大量使用电平转换芯片，一个电平转换芯片可能为多个功能芯片使用。电平转换芯片本身需要两个电源，这两个电源的开启应该由各个功能芯片控制。但在linux内核似乎没有适合于电平芯片的驱动模型。大家对这个问题有什么看法？
 
 ps，这里所说的驱动模型，如电源对应regulator模型，时钟对应clk模型等。 | [留言板](/message_board.html#c8829) |
| 2023-09-21 | xiaotonga | 了解device和device_driver相关概念和结构，但对应device和device_driver之间怎么匹配或建立联系呢？
 1.内核解析dts(device tree source)文件获知系统存在的硬件设备及其配置；
 2.device driver 通过设备树来获取系统中硬件设备，并与其通信。
 3.d… | [Linux设备模型(5)_device和device d](/device_model/device_and_driver.html#c8828) |
| 2023-09-19 | xiaotonga | 文中介绍的比较清楚，用户对kernel空间特定数据属性访问是通过sysfs来实现，具体形式为读写设备文件属性。文中对calss.c进行分析说明但对device driver实现kobj->ktype->sysfs_ops->show调用逻辑理解不是特别清楚；
 结合kernel driver的实现补充，进一步理解其调用… | [Linux设备模型(4)_sysfs](/device_model/dm_sysfs.html#c8827) |
| 2023-09-18 | tschome | 博主，可以问一下，你的这个图使用什么软件去画的呢，感觉很方便的样子。 | [tty驱动分析](/tty_framework/435.html#c8826) |
| 2023-09-18 | 支持大佬 | 支持大佬！ | [支持与合作](/support_us.html#c8825) |
| 2023-09-15 | xiaotonga | @wowo 昵称被限制，要换个马甲，ip被限制咋办呢，总不能再换设备吧 | [Linux设备模型(3)_Uevent](/device_model/uevent.html#c8824) |
| 2023-09-15 | xiaotonga | 1.个人理解kset_uevent_ops的逻辑和vfs中struct file_operations {}结构很类似（linux/v2.6.39.4/source/include/linux/fs.h#L1537）；
 2.用户只需读写设备文件，不用关心底层设备驱动，通过文件系统vfs的标准接口调用设备文件对应dev… | [Linux设备模型(3)_Uevent](/device_model/uevent.html#c8823) |
| 2023-09-14 | xiaotongs | @devin：1.动态创建：在内核空间动态分配内存。
 2.而不能静态定义或者位于堆栈之上：静态变量区、堆、栈是用户空间，用户空间分配内存需用通过C库或系统调用分配内存，实际上，用户空间分配的物理内存需通过内核来分配； | [Linux设备模型(2)_Kobject](/device_model/kobject.html#c8822) |
| 2023-09-14 | xiaotongs | kobject,内核基础设施，怎么和device（抽象设备）关联？怎么和driver关联？内核怎么通过kobject调用到对应的device？
 1. kobject会设备文件的形式在“sys”下出现，ket是kobject的集合，会将相似的kobj集合起来，在sys下也会以设备文件形式显示。
 2.ktype包含ko… | [Linux设备模型(2)_Kobject](/device_model/kobject.html#c8821) |
| 2023-09-13 | ziliang | @bsp：大佬讲的好详细呀 | [zRAM内存压缩技术原理与应用](/memory_management/zram.html#c8820) |
| 2023-09-13 | 黑桃JK | @红桃JK：捉 | [留言板](/message_board.html#c8819) |
| 2023-09-07 | 阿布 | @阿布：内核中io.h里使用dsb 定义了 io barriers。内核源码里的其他地方也有使用dsb 的，但有些地方的使用感觉有些不太好，比如android7.1 内核(msm-3.18)里 app_setting.c 75行中的mb()，其实完全可以使用smp_mb()，对吗？ | [DMB DSB ISB以及SMP CPU 乱序](/77.html#c8818) |
| 2023-09-07 | 阿布 | @阿布：在 real memory space 和io memory space交换数据时，由于io 设备可能对指令存在强依赖的关系（比如必须先给io 设备的时钟寄存器初始化，才能使能该io 设备的控制寄存器的使能bit），这种情况下需要使用dsb 指令去保证到达io设备的指令顺序是符合预期的(dsb 指令等待在此之前… | [DMB DSB ISB以及SMP CPU 乱序](/77.html#c8817) |
| 2023-09-06 | 阿布 | @forion：请问能结合点实际例子指点下DMB和DSB的使用吗？他们的应用场景有什么区别？如果在使用DSB的场景下使用了DMB，会出现什么情况？执行乱序除了是由多核cache 一致性引起的？还有别的地方也会造成执行乱序吗？我的理解是DMB避免了cache一致性造成的执行乱序，那么DSB在DMB的基础上到底为了应对什么… | [DMB DSB ISB以及SMP CPU 乱序](/77.html#c8816) |
| 2023-09-06 | 阿布 | 我一直不理解DMB 和DSB的应用场景，如果在使用DSB的场景下使用了DMB，会出现什么情况？请问能指点一下吗 | [DMB DSB ISB以及SMP CPU 乱序](/77.html#c8815) |
| 2023-09-06 | Caeser | 写的很清晰 非常赞呀 | [为什么会有“ARMv8A Architecture”这个](/armv8a_arch/why_armv8a_arch.html#c8814) |
| 2023-09-04 | Mana | 太棒了,23年未入门的新手就缺少这样系统、细致的讲解 | [蓝牙协议分析(1)_基本概念](/bluetooth/bt_overview.html#c8813) |
| 2023-09-01 | ychao | @bigpillow：拿锤子掉两下试试 | [linux内核中的GPIO系统之（1）：软件框架](/gpio_subsystem/io-port-control.html#c8812) |
| 2023-08-29 | 入行真的好难 | @wulala：期待wowo网站再次“忙碌起来” | [linux内核中的GPIO系统之（5）：gpio sub](/gpio_subsystem/pinctrl-and-gpio.html#c8811) |
| 2023-08-28 | wulala | wowo前辈 请问另有博客或者公众号吗 | [linux内核中的GPIO系统之（5）：gpio sub](/gpio_subsystem/pinctrl-and-gpio.html#c8810) |
| 2023-08-26 | wangdl | @testtest：分析的对啊，完全没问题 | [Linux内核同步机制之（一）：原子操作](/kernel_synchronization/atomic.html#c8809) |
| 2023-08-25 | kzf123456 | @冲：我支持了39。99 | [支持与合作](/support_us.html#c8808) |
| 2023-08-25 | Roy | @linuxer 兄，
 关于您讨论的电压的本质，从静电场，电势差考虑，甚至加上欧姆定律都可以无缝缝合。
 但是，假设考虑超导呢？
 假设有一段超导体一直延伸到无限远处，那么无限远处的电势是多少？
 
 电压这个概念是否真的是某种物质的內秉属性吗？ | [基本电路概念之（一）：什么是电压？](/basic_subject/voltage.html#c8807) |
| 2023-08-25 | Roy | @linuxer 兄，令公子要好好培养。
 我家两个小儿，目前还无法开窍。
 整个夏天，几乎每天都是一边在电脑上玩迷你世界，一边让奶奶喂饭。 | [基本电路概念之（一）：什么是电压？](/basic_subject/voltage.html#c8806) |
| 2023-08-21 | Kiddy | 这个问题在内核5.15也存在，但是我看好像合入了这个patch。博主能给点思路吗 | [关于numa loadbance的死锁分析](/linux_kenrel/482.html#c8805) |
| 2023-08-10 | lifetjk | @hh20194362：可以啊，直接使用CPU hotplug不就可以直接减核了吗？ | [Linux CPU core的电源管理(1)_概述](/pm_subsystem/cpu_core_pm_overview.html#c8804) |
| 2023-08-08 | 冲 | 支持10块大洋，获准良多 | [支持与合作](/support_us.html#c8803) |
| 2023-08-04 | Marvin | 这个系列写的太好了，非常有帮助，感谢！ | [DRAM 原理 5 ：DRAM Devices Orga](/basic_tech/343.html#c8802) |
| 2023-08-04 | hh20194362 | 请教wowo专家一个问题，是否可以不通过suspend流程，直接对CPU进行减核操作呢？如果没有冻结线程，直接调用函数freeze_secondary_cpus，会不会使某个正在运行的CPU下电，导致业务中断呢？期待您的答复。 | [Linux CPU core的电源管理(1)_概述](/pm_subsystem/cpu_core_pm_overview.html#c8801) |
| 2023-08-02 | sleep | 我是初学者，首先感觉大佬很强，文章写的也很细，但少了点框架性的概述，感觉文章结构，内容组织和语句上可以改进下。文章开始我觉得可以先描述下interrupt-controller，irq-domain，irq-desc等几个对象的组织方式和对应关系或所属关系，稍稍具象化一点，不然一直说添加domain，添加映射其实是比较… | [Linux kernel的中断子系统之（二）：IRQ D](/irq_subsystem/irq-domain.html#c8800) |
| 2023-07-21 | yeee | @吴兵：pclk还没注册？ | [Linux common clock framework](/pm_subsystem/clk_overview.html#c8799) |
| 2023-07-21 | aha | 从arm64的setup_arch来看，arm64架构不需要做platform匹配，只检查了root节点是否有model或者compatible。也就是说不同的arm64的soc都是无差异的setup arch过程，不需要实现struct machine_desc结构体中各种回调。这是因为arm64的soc真的不需要，… | [Device Tree（三）：代码分析](/device_model/dt-code-analysis.html#c8798) |
| 2023-07-21 | 波加查在北京 | 这里的意思是kernel层的wakelock为android层的提供了接口，android的wakelock就是基于kernel的wakelock实现的，而kernel的wakelock本质上又是基于wakeup source。
 相当于三层套娃，android wakelock —> kernel wakelock … | [Linux电源管理(9)_wakelocks](/pm_subsystem/wakelocks.html#c8797) |
| 2023-07-12 | iptvphone | 认真学习！感谢主人的分享！ | [关于蜗窝](/about.html#c8796) |
| 2023-07-11 | zxq | 看的不够仔细，A处已经被我们自己设置了pending bit，clear之前别人没有机会再设置pending bit，也不存在误清被人设置的pending bit。 | [Linux内核同步机制之（九）：Queued spinl](/kernel_synchronization/queued_spinlock.html#c8795) |
| 2023-07-11 | zxq | 3、Pending owner task
 
 val = queued_fetch_set_pending_acquire(lock);---------A
 
 if (unlikely(val & ~_Q_LOCKED_MASK)) {------------B
 
  if (!(val & _Q_PENDIN… | [Linux内核同步机制之（九）：Queued spinl](/kernel_synchronization/queued_spinlock.html#c8794) |
| 2023-06-30 | Bright-Ho | @wowo：2. 所谓的event机制，正是基于设备模型（uevent）的封装。
 wowo，你好！
 这句话有依据吗？event事件作为input子系统的事件上报机制，与设备模型（uevent）有关系吗？ | [Linux设备模型(7)_Class](/device_model/class.html#c8793) |
| 2023-06-27 | uucad | @炒河粉的：L1I, 指令cache? | [浅谈Cache Memory](/memory_management/458.html#c8792) |
| 2023-06-20 | zzzz | @wowo：sched_class是调度类，linux调度类中包含cfs（完全公平调度），rt（实时调度）以及idle等。优先级由高到低为rt->cfs->idle。每个调度类有其对应的运行队列，在linux调度选择下一个需要运行的进程时，会按照优先级由高到低扫描每一个调度类，找到可以运行的进程。也就是说，rt调度类的… | [Linux cpuidle framework(1)_概](/pm_subsystem/cpuidle_overview.html#c8791) |
| 2023-06-19 | 平平淡淡 | 太赞了，多谢博主！ | [关于蜗窝](/about.html#c8790) |
| 2023-06-15 | ty | @lin：23年前来学习 | [Linux设备模型(1)_基本概念](/device_model/13.html#c8789) |
| 2023-05-31 | yanl1229 | 终于等到更新了。 | [Linux读写锁逻辑解析](/kernel_synchronization/rwsem.html#c8788) |
| 2023-05-29 | 5song | @立志学linux：一般handle_irq()会进行如下操作，可参考(kernel/irq/chip.c: void handle_edge_irq(struct irq_desc *desc))：
 
 调用中断描述符中的底层chip driver进行mask以及中断ACK回调，进行IRQ flow control… | [linux kernel的中断子系统之（三）：IRQ n](/irq_subsystem/interrupt_descriptor.html#c8787) |
| 2023-05-26 | 立志学linux | 有没有大佬知道，high level handler 和 通过request_threaded_irq注册的那个的handler（也就是irq_desc->irqaction->handler）是什么关系呀 | [linux kernel的中断子系统之（三）：IRQ n](/irq_subsystem/interrupt_descriptor.html#c8786) |
| 2023-05-26 | 立志学linux | @Magicmanoooo：既然这样，那为什么不干脆用好几个不同的变量呢？还是说percpu变量就是等于定义了好几个不同的变量？ | [Linux内核同步机制之（二）：Per-CPU变量](/kernel_synchronization/per-cpu.html#c8785) |
| 2023-05-18 | laoyekang | 推荐一个油管视频 对于此模块各个时间的计算有一个初步介绍 对理解此模块各种公式计算有帮助
 www.youtube.com/watch?v=E1uyXn0kBAc | [Linux时间子系统之（四）：timekeeping](/timer_subsystem/timekeeping.html#c8784) |
| 2023-05-08 | 顶点软件 | 你写得非常清晰明了，让我很容易理解你的观点。 | [futex基础问答](/kernel_synchronization/futex.html#c8782) |
| 2023-05-08 | eillon | @Egan：需要ARMv8.4硬件支持 | [TLB flush操作](/memory_management/tlb-flush.html#c8781) |
| 2023-05-06 | Yogi | 图片看不见了，是否可以重新上传一下 | [DRAM 原理 5 ：DRAM Devices Orga](/basic_tech/343.html#c8780) |
| 2023-05-05 | Tptogiar | 正在入门linux kernel，入门KVM虚拟化，学习kernel技术
 学kernel，学虚拟化，每每有幸能阅读到高质量的文章，我都会兴奋，而站主的文章就是这样的文章 | [关于蜗窝](/about.html#c8779) |
| 2023-04-29 | BMC开发 | 踏实做的需要支持，世界因为分享而美妙 | [支持与合作](/support_us.html#c8778) |
| 2023-04-28 | storage | @呜啦啦：好问题，确实是这样 | [Linux内核同步机制之（六）：Seqlock](/kernel_synchronization/seqlock.html#c8777) |
| 2023-04-26 | Hector | 果断收藏 | [关于蜗窝](/about.html#c8776) |
| 2023-04-23 | 123 | @wowo：以上除“Profile”外的每一个定义，Service、Characteristic、Characteristic Properties、Characteristic Value、Characteristic Descriptor等等，都是作为一个Attribute存在的，具备第8章所描述的Attribut… | [蓝牙协议分析(3)_蓝牙低功耗(BLE)协议栈介绍](/bluetooth/ble_stack_overview.html#c8775) |
| 2023-04-19 | ecjtusbs | @zecard：“两块相邻的内存块都被申请过 影子内存都是0” 这种情况的越界检测是否有效，不知道答主有没有明确的结论，我的感觉应该无法区分。 | [KASAN实现原理](/memory_management/424.html#c8774) |
| 2023-04-18 | nemo | wakeup处理等过个知识点 = > 多个知识点 | [Linux电源管理(6)_Generic PM之Susp](/pm_subsystem/suspend_and_resume.html#c8773) |
| 2023-04-12 | melo | @鱼儿：我觉得: 
 假设我们分配4个page分别保存
 只有4个pages, 第一个page存放pgd, 第二个放pud, 第三个放pmd, 第四个放pte
 pte最多放512个entries
 为何只算level3呢？如果低于level3, 需要的pages就多于4个了 | [内存初始化（上）](/memory_management/mm-init-1.html#c8772) |
| 2023-04-12 | icy_river | 从store_buffer和invalid_queue的角度, 能很好的理解rmb(), wmb(), mb(); 怎么从这种硬件的角度理解半屏障呢? ldaxr, stxr这样的指令执行之后, 在store_buffer和invalid_queue上,是个怎样的行为呢?
 
 最终从外部observer看起来, 半屏… | [Why Memory Barriers？中文翻译（上）](/kernel_synchronization/Why-Memory-Barriers.html#c8771) |
| 2023-04-11 | 一只卤蛋 | 作者现在不更新了么，还是换了平台了呢，有没有朋友知道的 | [致驱动工程师的一封信](/device_model/429.html#c8770) |
| 2023-04-11 | 一只卤蛋 | 写的真好哇，逻辑好清楚 | [中断唤醒系统流程](/irq_subsystem/irq_handle_procedure.html#c8769) |
| 2023-04-10 | hulianqing | @devin：我的理解是：1、把kobject定义在你的自定义结构体内，然后自定义结构体动态分配 2、直接单独分配kobject | [Linux设备模型(2)_Kobject](/device_model/kobject.html#c8768) |
| 2023-04-07 | qliangw | 学了小半年相关linux kernel知识，再看博主的文章真的是醍醐灌顶！！！感谢博主的分享，相关文章值得细读细品，满满干货 | [Linux设备模型(9)_device resource](/device_model/device_resource_management.html#c8767) |
| 2023-04-06 | icy_river | @dream：在你假设的场景是,功能是没问题的; 但是这样B的时间片不是完全浪费了吗? | [Linux内核同步机制之（四）：spin lock](/kernel_synchronization/spinlock.html#c8766) |
| 2023-04-06 | icy_river | @bsp：1. sev只有sev/sevl两种, 无法给指定core发event;
 2. 同时自旋的core太多的话, cache同步开销就不能忽略了;
 3. kernel 5.10, ticket spinlock已经换成qspinlock; | [Linux内核同步机制之（四）：spin lock](/kernel_synchronization/spinlock.html#c8765) |
| 2023-04-04 | cc | @EE：控制 | [蓝牙协议分析(10)_BLE安全机制之LE Encryp](/bluetooth/le_encryption.html#c8764) |
| 2023-04-02 | sql | 感动与敬佩，一点心意，聊表支持与感谢。这个世界会好的~ | [支持与合作](/support_us.html#c8763) |
| 2023-03-30 | XuLiDown | @code_搬运工：个人感觉这里的表述可能有点问题。sg_dma_address 代表的应该是内存块在总线地址空间中的基地址，dma_length 代表的则是内存块在总线地址空间中的长度 | [Linux kernel scatterlist API](/memory_management/scatterlist.html#c8762) |
| 2023-03-29 | leo | 如果切入的是普通进程，那么这时候进程的地址空间已经切换了，也就是说在A--->B进程的过程中，进程本身尚未切换，而进程的地址空间已经切换到了B进程了。这样会不会造成问题呢?还好，呵呵，这时候代码执行在kernel space，A和B进程的kernel space都是一样一样的啊，即便是切了进程地址空间，不过内核空间实际… | [进程切换分析(1)：基本框架](/process_management/context-switch-arch.html#c8761) |
| 2023-03-24 | YG | 博主14年写的文章，现在读起来依然受益匪浅，佩服！！
 真想知道博主是怎么一步步到达这种水平的 | [linux kernel的中断子系统之（四）：High ](/irq_subsystem/High_level_irq_event_handler.html#c8760) |
| 2023-03-23 | 单手御龙 | 蜗窝的大群（457024058）已经加满了，我建了个小群（733620975）,方便大家沟通交流（非官方） | [蜗窝微信群问题整理](/tech_discuss/question_set_1.html#c8759) |
| 2023-03-23 | cc | 博主你好，说起来是在其他博文里看的东西，但是有个问题一直没有解决。问题是这样的，检测充电器的插拔，插和拔两个动作产生两种中断，但是只有一个检测中断的引脚。我看到文章的示例中，设备节点的interrupts属性中只有一个中断向量，但是获取中断号时却可以得到两个中断号，很疑惑，如果博主或者其他读者看到我的问题，可以解答一下… | [Linux kernel的中断子系统之（一）：综述](/irq_subsystem/interrupt_subsystem_architecture.html#c8758) |
| 2023-03-20 | Thomas | 前辈你好，阅读你的文章受益良多。linuxer新手前来讨论。对以下两段话还是感觉有不对的地方。
 1.在"Linux设备模型(4)_sysfs”中，我们有讲到，大多数时候，attribute文件的读写数据流为：vfs---->sysfs---->kobject---->attribute---->kobj_type--… | [Linux设备模型(5)_device和device d](/device_model/device_and_driver.html#c8757) |
| 2023-03-19 | shousi | @农夫山泉：我理解是进exception的时候，硬件关闭了CPU的Interrupt位。直到irq_exit里面才主动打开。可以在qmeu里打个断点看下。 | [linux kernel的中断子系统之（八）：softi](/irq_subsystem/soft-irq.html#c8756) |
| 2023-03-18 | devin | 动态创建
 "前面讲过，Kobject必须动态分配，而不能静态定义或者位于堆栈之上，它的分配方法有两种。"这里笔误了吗？ | [Linux设备模型(2)_Kobject](/device_model/kobject.html#c8755) |
| 2023-03-15 | double_qiang | @呜啦啦：不是啊，write thread把reader thread给抢占了，然后将对应的B node释放后，之后reader thread还会再重新进临界区，这时候再去遍历链表时，链表中已经不存在B node，又怎么会去访问B node呢 | [Linux内核同步机制之（六）：Seqlock](/kernel_synchronization/seqlock.html#c8754) |
| 2023-03-14 | double_qiang | @九五二七：我的理解抢占时机可以简化成两种，一种是依赖中断发生调度时，另外一个就是当前进程主动调用schedule，显然后面这种的抢占时机肯定是不存在原子操作的 | [Linux内核同步机制之（一）：原子操作](/kernel_synchronization/atomic.html#c8753) |
| 2023-03-13 | g | @linuxer：请问书名是什么？ | [逆向映射的演进](/memory_management/reverse_mapping.html#c8752) |
| 2023-03-13 | 禅机子 | @bsp：想问一下，最近我遇到一个问题，就是user_task，存在扫描文件的操作，如果刚好在suspend流程中，会出现freezing of tasks。
 有什么解决思路嘛，麻烦啦 | [Linux进程冻结技术](/pm_subsystem/237.html#c8751) |
| 2023-03-08 | hymmsx | @litao6169：你这个结果计算出来是A6200000和他设的A6200000不一样？ | [KASLR](/memory_management/441.html#c8750) |
| 2023-03-08 | hymmsx | @litao6169：你这个结果计算出来是A6200000和他设的A6200000不一样？ | [KASLR](/memory_management/441.html#c8749) |
| 2023-03-06 | jqdeng | @Zaiqiang：用的已经不是启动时的页表，而是在early_fixmap_init里面使用了bm_pud/bm_pmd/bm_pte这三个数组重新建立了映射 | [内存初始化（上）](/memory_management/mm-init-1.html#c8748) |
| 2023-02-28 | 小鱼儿 | 看的很舒服啊 | [CFS任务的负载均衡（概述）](/process_management/load_balance.html#c8747) |
| 2023-02-24 | 550W | 好问题。
 这个是因为:
 grq->avg.load_avg = 
 (cfs_rq->load.weight * delta_time) / LOAD_AVG_MAX
 当这个CPU一直运行,idle时间很少的时间，可以近似认为delta_time = LOAD_AVG_MAX，也就是可以用load_avg来模拟l… | [CFS调度器（3）-组调度](/process_management/449.html#c8746) |
| 2023-02-23 | 龟仙人 | 与诸君共勉！
 认同站长的理念“透透彻彻，明明白白”
 拒绝在奔走忙碌中无所长进，争取在沟通思考中共同进步。 | [关于蜗窝](/about.html#c8745) |
| 2023-02-17 | bsp | @bsp：swap & page fault流程
 1:将待swap的page 加入到swapcache中；
 2:解除task和该page的映射关系；
 3:通过pageout 进行zram压缩，并将此page压到某个buffer中；
 4:压缩完成后，选择性从swapcache中free该page（比如swapca… | [zRAM内存压缩技术原理与应用](/memory_management/zram.html#c8744) |
| 2023-02-16 | yayaya | 用户设置nice值后在内核中会有NICE_TO_PRIO宏转换成优先级，我们平常看到的nice值都为0不代表内核没有对其他nice值做处理，看下内核代码就会明白的 | [O(n)、O(1)和CFS调度器](/process_management/scheduler-history.html#c8743) |
| 2023-02-16 | yayaya | @威点零：任务主动休眠或系统调用是随机的，与tick无关，也就是在两个tick之间就有可能发生，这时就要判断实际的执行时间，而不是根据tick数确定 | [O(n)、O(1)和CFS调度器](/process_management/scheduler-history.html#c8742) |
| 2023-02-16 | yayaya | @markened：是实际时间 | [O(n)、O(1)和CFS调度器](/process_management/scheduler-history.html#c8741) |
| 2023-02-14 | testtest | ldrex和strex的方案，如果三个线程竞争是不是有问题？如下场景
 
 ldrex 1 => r1		thread1
 modify r1++			thread1
 ldrex 1 => r2		thread2
 modify r2++			thread2
 strex r2			thread2 success
 … | [Linux内核同步机制之（一）：原子操作](/kernel_synchronization/atomic.html#c8740) |
| 2023-02-06 | Li Chen | dts需要准确的描述硬件，如果SoC的所有clk相关setting都是放在一个module，比如clk module或者某个system controller，那么就应该放在一个node里，否则应该放在自己独立的node | [Linux common clock framework](/pm_subsystem/clock_provider.html#c8739) |
| 2023-02-03 | 耗子尾汁 | QQ群现在加不了了吗？ | [蜗窝微信群问题整理](/tech_discuss/question_set_1.html#c8738) |
| 2023-02-02 | 东城阿大 | 本文中的“busy cpu" 改为 "active cpu"与 idle相对更容易理解些，busy指的是忙，本来讲的是负载均衡，如果还是busy cpu去拉取其它进程过来，这地方会让人费解，如果看成是active cpu的话，这样就容易理解了。没有进入idle状态的，还在运行的。 | [CFS任务的负载均衡（load balance）](/process_management/load_balance_detail.html#c8737) |
| 2023-02-01 | woda | 群满了 | [关于蜗窝](/about.html#c8736) |
| 2023-02-01 | bsp | ticket-based-spinlock有个重大问题：
 假如当CPU0获取了spinlock，而CPU1、CPU2、CPU3...在等锁，在CPU0 spin_unlock时通过sev/stlr唤醒其它所有所有CPU去check是否轮到自己；我们通过ticket可以知道lock->next是哪个CPU，其实只需要唤… | [Linux内核同步机制之（九）：Queued spinl](/kernel_synchronization/queued_spinlock.html#c8735) |
| 2023-01-31 | bsp | ticket-based-spinlock有个问题，
 CPU0获取了spinlock，CPU1、CPU2、CPU3...在等锁时，CPU0通过spinunlock中的sev唤醒其它所有所有CPU去check是否轮到自己；既然我们通过ticket知道了lock->next是哪个CPU，其实只需要唤醒对应CPU上的tas… | [Linux内核同步机制之（四）：spin lock](/kernel_synchronization/spinlock.html#c8734) |
| 2023-01-31 | bsp | @dream：B如果为rt线程，SCHED_FIFO时，是不考虑时间片的； | [Linux内核同步机制之（四）：spin lock](/kernel_synchronization/spinlock.html#c8733) |
| 2023-01-28 | maan008 | @飞鸟：wowo还在呢啊~~~ 以为你离开了啊 同事推荐的网站，受益匪浅，感谢感谢~ | [留言板](/message_board.html#c8732) |
| 2023-01-20 | 红桃JK | 今天下午1点偶然发现这个网页，原本想简单看看，没想到一直看到晚上八点半。
 写的太好了，每部分内容都十分具体详细。
 直接转粉，收藏，以后慢慢看 | [留言板](/message_board.html#c8731) |
| 2023-01-17 | bang | @wmzjzwlzs：可以的，如ARM64通过PTE页表控制的，是否是cache的还是no-cache的，不同的虚拟地址对应不同PTE页表。 | [浅谈Cache Memory](/memory_management/458.html#c8730) |
| 2023-01-05 | learner | @donbear：PELT虽然是按se计算的。但是因为pelt最终是用来衡量cpu超载、cpu负载均衡的，所以时间是从cpu的角度看待的，对于一个cpu来说，统计的都是几何级数最大值时间段内的负载，所以对于每个任务都要计算在这段时间内的负载。 | [PELT算法浅析](/process_management/pelt.html#c8729) |
| 2023-01-04 | bsp | 内存压缩的调用路径中，add_to_swap并不会直接call pageout，add_to_swap只是将page变成SwapPage并和swap_entry建立对应关系；
 并且，add_to_swap时，page对应的mapping还未unmap；
 流程大致是：先add_to_swap，后try_to_unma… | [zRAM内存压缩技术原理与应用](/memory_management/zram.html#c8728) |
| 2022-12-28 | 农夫山泉 | 关本地中断实际上是禁止了top half和bottom half抢占当前进程上下文的运行？这个是怎么实现的，看local_irq_disable()的代码并没有关软中断/ | [linux kernel的中断子系统之（八）：softi](/irq_subsystem/soft-irq.html#c8727) |
| 2022-12-20 | abccdeg | 篇幅不多，但讲得非常透彻，尤其实验过程，赞！ | [文件系统和裸块设备的page cache问题](/filesystem/439.html#c8726) |
| 2022-12-20 | abccdeg | @judy：个人的一点理解，不知是否正确：自旋锁解锁时、系统调用返回用户空间时、当前时间片用完（hrtick到期时）。 | [O(n)、O(1)和CFS调度器](/process_management/scheduler-history.html#c8725) |
| 2022-12-18 | judy | "在当前进程被抢占的场景下，调度并不是立刻发生，而是延迟执行，具体的方法是设定当前进程的need_resched等于1，然后静静的等待最近一个调度点的来临，当调度点到来的时候，内核会调用schedule函数，抢占当前task的执行。"请问“调度点”是什么呢？是谁设置的呢？ | [O(n)、O(1)和CFS调度器](/process_management/scheduler-history.html#c8724) |
| 2022-12-15 | Yaksama | @dream：个人认为spinlock本身就是一种轻量级的锁，设计初衷除了考虑中断访问临界区资源的情况，还有一个就是避免过多进程上下文切换带来的开销。
 如果不disable preempt，的确拥有锁的线程早晚有得到执行的一天，但这种情况为什么不直接用mutex呢，而且线程获取spinlock之后执行的任务都是轻量级… | [Linux内核同步机制之（四）：spin lock](/kernel_synchronization/spinlock.html#c8723) |
| 2022-12-14 | ecjtusbs | 2022年12月14日
 读了好几遍，每次感觉受益匪浅！
 前人栽树后人乘凉。感谢前辈的无私分享。 | [Linux kernel的中断子系统之（六）：ARM中断](/irq_subsystem/irq_handler.html#c8722) |
| 2022-12-14 | Li Chen | > 实际上是从TEXT_OFFSET开始的，偏移这么一小段内存估计是为了bootloader和kernel之间传递一些信息
 
 不是, 这段当初是给swapper page table用的 | [ARM64的启动过程之（二）：创建启动阶段的页表](/armv8a_arch/create_page_tables.html#c8721) |
| 2022-12-13 | 炒河粉的 | 为什么有的一级缓存read-only？这个read-only该怎么理解呢 | [浅谈Cache Memory](/memory_management/458.html#c8720) |
| 2022-12-12 | Egan | ARM architecture现在有支持TLB range的 | [TLB flush操作](/memory_management/tlb-flush.html#c8719) |
| 2022-12-11 | wmzjzwlzs | smp_mb实际是dmb ish，在inner shareable内的多core管用.如果是多个cluster之间的core应该是dmb osh吧？linux支持多cluster为啥smp_mb不是dmb osh？ | [Linux内核同步机制之（三）：memory barri](/kernel_synchronization/memory-barrier.html#c8718) |
| 2022-12-10 | marvin263 | 时间片太小，调度就会更为频繁。从v5.13起，加了个开关，确保最小执行时间为sysctl_sched_min_granularity的。
 
 http(s)://github.com/torvalds/linux/commit/0c2de3f054a59f15e01804b75a04355c48de628c
 
 T… | [CFS调度器（6）-总结](/process_management/452.html#c8717) |
| 2022-12-09 | xxxxxxx | 赞~ | [DMB DSB ISB以及SMP CPU 乱序](/77.html#c8716) |
| 2022-12-08 | Roy | 拜阅
 
 Guest OS（Linux kernel、window等）位于EL1
 是否大致逻辑如下：
 若实现Hypervisor（EL2），则EL1可运行若干GuestOS，否则EL1运行OS。
 
 只有在异常发生时（或者异常处理返回时），才能切换Exception level（...）
 SMC或HVC 是否… | [ARMv8-a架构简介](/armv8a_arch/armv8-a_overview.html#c8715) |
| 2022-12-08 | Roy | 拜阅
 linuxer、forion、wowo等同学，都表现（除）出了极大的兴趣， //除 ->出
 建议修改
 从最初的ARM7（v4），ARM9/9E（v5），到后来的ARM11（v6）， | [为什么会有“ARMv8A Architecture”这个](/armv8a_arch/why_armv8a_arch.html#c8714) |
| 2022-12-04 | muzimuke | "它实际上会本cpu的进程上下文和中断上下文访问"
 文中的这句话是不是写错了呀？ | [Linux内核同步机制之（三）：memory barri](/kernel_synchronization/memory-barrier.html#c8713) |
| 2022-12-01 | 卷心菜 | 请问红区的size是多大？ | [SLUB DEBUG原理](/memory_management/427.html#c8712) |
| 2022-12-01 | kongsuozt | @smcdef：vmalloc也可以做，不过得自己去实现shadow memory的映射、状态更新以及分配释放的hook插入 | [KASAN实现原理](/memory_management/424.html#c8711) |
| 2022-11-30 | doran | @zach：你的理解是对的，但是不够完善 | [浅谈Cache Memory](/memory_management/458.html#c8710) |
| 2022-11-29 | melo | @11号tony老师：1 card0这个节点, 可以通过open打开, 获取crtc encoder connector fb等资源, 实现设置分辨率, 刷新率等设置
 renderxx这个节点, 应该是card0的子集, 只有3d加速部分, 实际没看到过怎么打开使用
 fb这个是一个被drm淘汰下来的陈旧显示模块
 … | [Linux graphic subsystem(2)_D](/graphic_subsystem/dri_overview.html#c8709) |
| 2022-11-29 | abcdggg | kmem_cache.kmem_cache_node.list_lock这个锁仅用于写kmem_cache_node结构成员的场合（读操作未见加锁），那么就有一定概率出现错乱 | [图解slub](/memory_management/426.html#c8708) |
| 2022-11-29 | abcdggg | 请教一下，假如一个cpu在kmem_cache_destroy销毁句柄，另一个cpu在kmem_cache_alloc使用句柄分配内存，二者如何互斥？没有看到加锁的情形。 | [图解slub](/memory_management/426.html#c8707) |
| 2022-11-29 | sxr | @sxr：哦哦，没事了，貌似是加载很慢，我过了五六分钟就出来了 | [DRAM 原理 1 ：DRAM Storage Cell](/basic_tech/307.html#c8706) |
| 2022-11-29 | sxr | 图片没挂，但是加载不出来，f12查看源代码找到图片链接是能打开的，求修正 | [DRAM 原理 1 ：DRAM Storage Cell](/basic_tech/307.html#c8705) |
| 2022-11-29 | wowo | @飞鸟：抱歉哈，没来得及处理，已经修复了。
 感谢~~~ | [留言板](/message_board.html#c8704) |
| 2022-11-24 | joker | 博客很好，果断收藏了 | [关于蜗窝](/about.html#c8702) |
| 2022-11-22 | 飞鸟 | 站内搜索为啥不支持了呢？ | [留言板](/message_board.html#c8701) |
| 2022-11-17 | Ren Zhijie | E、将detach_tasks函数摘下的任务挂入到src rq上去。由于detach_tasks、attach_tasks会进行多轮，ld_moved记录了总共迁移的任务数量，cur_ld_moved是本轮迁移的任务数
 
 将detach_tasks函数摘下的任务挂入到*dst_rq*上去。 | [load_balance函数代码详解](/process_management/load_balance_function.html#c8700) |
| 2022-11-16 | 凉冰 | 什么时候出一篇致入门小白的一封信啊，好多的点到为止，小白真就点到为止了。 | [致驱动工程师的一封信](/device_model/429.html#c8699) |
| 2022-11-15 | Ren Zhijie | 有个疑惑，问题如下：
 二、周期性负载均衡->2、均衡处理->D、每个level的sched domain都会计算下一次均衡的时间点，这里记录最近的那个均衡时间点,是怎么推导出后面的降低均衡次数，避免不必要均衡带来的开销的结论的呢？ 我理解这里应该是保证tick可以触发sd层级中最接近的那个next_balance时间… | [CFS任务的负载均衡（load balance）](/process_management/load_balance_detail.html#c8698) |
| 2022-11-07 | lin | @alilili：22年前来学习 | [Linux设备模型(1)_基本概念](/device_model/13.html#c8697) |
| 2022-11-06 | 木木在努力 | 刚刚跨入linux工作的大军中，真的蜗蜗写的内容的好详细，对我的帮助真的好大，爱了 | [关于蜗窝](/about.html#c8696) |
| 2022-11-02 | llama | @Toni：用内嵌DMA是标准做法。用系统的DMA理论上是可以的。但是这样就要每个系统都要做芯片设计上的集成。这样比起即插即用的内嵌DMA，成本上差太多了。 | [Linux DMA Engine framework(3](/linux_kenrel/dma_controller_driver.html#c8695) |
| 2022-10-26 | 刘 | 第一个问题就是：为何irq_set_chip接口函数使用irq_get_desc_lock来获取中断描述符，而irq_set_irq_type这个函数却需要irq_get_desc_buslock呢？其实也很简单，irq_set_chip不需要访问底层的irq chip（也就是interrupt controller）… | [linux kernel的中断子系统之（三）：IRQ n](/irq_subsystem/interrupt_descriptor.html#c8694) |
| 2022-10-26 | 王 | 不错，休闲刚好学习一下 | [futex基础问答](/kernel_synchronization/futex.html#c8693) |
| 2022-10-24 | bsp | schedtuil最初的设计不是为big_little这种架构吧？毕竟inte在l2016年写scheutil时，intel还没开始搞大小核。只是后来发现schedutil用来给arm的大小核调频 也能更好的匹配上？ | [schedutil governor情景分析](/process_management/schedutil_governor.html#c8692) |
| 2022-10-21 | 小鱼儿 | 作为IC公司，确实没有办法 | [X-002-HW-S900芯片boot from USB](/x_project/s900_hw_adfu.html#c8691) |
| 2022-10-21 | 小鱼儿 | 很难不支持 | [关于蜗窝](/about.html#c8690) |
| 2022-10-18 | 奥特曼 | @奥特曼：补充: kernel版本是4.14.73
 启动时有
  Clockevents: could not switch to one-shot
  Clockevents: could not switch to one-shot
  Clockevents: could not switch to one-s… | [Linux时间子系统之（二）：软件架构](/timer_subsystem/time-subsyste-architecture.html#c8689) |
| 2022-10-18 | 奥特曼 | 你好 我有一个问题
 在用户层调用usleep(1000)时，发现实际用时有10000us(100HZ的配置)，但是我是有自己的HRTIMER的，不知道为啥没起效，经过排查，我自己注册的clk_event被系统的dummy_timer替代作为了pre_cpu的clk_evnent （我是ARMV7的），而我注册的clk… | [Linux时间子系统之（二）：软件架构](/timer_subsystem/time-subsyste-architecture.html#c8688) |
| 2022-10-17 | yibai | 很棒，感谢分享 | [支持与合作](/support_us.html#c8687) |
| 2022-10-12 | DyalnW | 正在学习device tree，感谢大佬的文章 | [Device Tree（一）：背景介绍](/device_model/why-dt.html#c8686) |
| 2022-10-12 | wmzjzwlzs | @bsp：多谢, 可以同时存在的吗?同一个物理地址ioreamp到虚拟地址a时开启cache，ioreamp到虚拟地址b时关闭cache,然后同时使用a与b | [浅谈Cache Memory](/memory_management/458.html#c8685) |
| 2022-10-11 | bsp | @wmzjzwlzs：当然可以，最基本的操作，内核里可以参考ioreamp； | [浅谈Cache Memory](/memory_management/458.html#c8684) |
| 2022-10-09 | 补零补零补零 | @zxl：通过代码分析一下，本人菜鸡，谨慎阅读
 
 ---creat_pinctrl
 对于其他的设备使用pinctrl子系统来设置引脚，获取pinctrl 时解析设备树的步骤是这样的，
 循环获取pinctrl-n，通过state = 0 ，依次解析各个state --- pinctrl_dt_to_map 函数
… | [Linux内核中的GPIO系统之（3）：pin cont](/gpio_subsystem/pin-controller-driver.html#c8683) |
| 2022-10-08 | wmzjzwlzs | linux arm，同一个物理地址能否映射到虚拟地址a时开启cache，映射到虚拟地址b时关闭cache？这样cpu访问a经过cache，访问b就不经过cache | [浅谈Cache Memory](/memory_management/458.html#c8682) |
| 2022-09-30 | Aero | @蚂蚁的爸爸：人家说的就是妥的意思. 别反复嚼舌根子, 自己理解错了还用昵称骂人, 这是不对的. 
 这里是技术论坛, 蚂蚁说话一直都客客气气, 你别把扣帽子WG气息带到这里来. 
 你的回复暴露你的智商, 你的昵称又暴露了你的素质. 换了马甲再来吧. | [u-boot启动流程分析(1)_平台相关部分](/u-boot/boot_flow_1.html#c8681) |
| 2022-09-30 | ymmmy | 大学四年令我一直困惑的是如何理解三极管的寄生电容，现在理解了，邻近器件不同的电位使然，器件也可以是导线。 | [基本电路概念之（二）：什么是电容？](/basic_subject/what-is-capacitor.html#c8680) |
| 2022-09-30 | 11 | 第一次进行读写的时候需要precharge吗？这个precharge为什么叫做关闭行？明明是读写前的准备工作呀。 | [DRAM 原理 3 ：DRAM Device](/basic_tech/321.html#c8679) |
| 2022-09-28 | 三变 | wowo是一个团队吗？还是一个人？
 真的太渊博了，几乎覆盖整个底层驱动。。。 | [留言板](/message_board.html#c8678) |
| 2022-09-28 | xinhe | mark, 很顺理成章的讲解 | [为什么会有文件系统(二)](/filesystem/396.html#c8677) |
| 2022-09-28 | xinhe | @wolf：我还以为是我这边的问题呢 | [eMMC框架及其初始化](/filesystem/329.html#c8676) |
| 2022-09-27 | blazer | @tuhh：我也觉得参考文献列出来好一些，毕竟cache的这些性质俺们也不一定懂呢 | [Linux内核同步机制之（三）：memory barri](/kernel_synchronization/memory-barrier.html#c8675) |
| 2022-09-15 | Bin | @郭健：label在设备树中用，aliases中定义的别名在驱动源码中用 | [Device Tree（二）：基本概念](/device_model/dt_basic_concept.html#c8674) |
| 2022-09-06 | schspa | @raceant：hwspinlock是外部IP提供的（不同厂家的IP会有不同），每次操作都需要通过MMIO来方位外部寄存器(Device nGnRnE)，速度会慢的多. 这种的每次访问都不会经过cache. | [Atomic operation in aarch64](/armv8a_arch/492.html#c8673) |
| 2022-09-06 | schspa | @raceant：hwspinlock是外部IP提供的（不同厂家的IP会有不同），每次操作都需要通过MMIO来方位外部寄存器(Device nGnRnE)，速度会慢的多. 这种的每次访问都不会经过cache. | [Atomic operation in aarch64](/armv8a_arch/492.html#c8672) |
| 2022-09-06 | schspa | @raceant：hwspinlock是外部IP提供的（不同厂家的IP会有不同），每次操作都需要通过MMIO来方位外部寄存器(Device nGnRnE)，速度会慢的多. 这种的每次访问都不会经过cache. | [Atomic operation in aarch64](/armv8a_arch/492.html#c8671) |
| 2022-08-25 | 影 | 有没有办法在申请高精度定时器时，将该定时器绑定到特定的CPU核上？ | [Linux时间子系统之（十三）：Tick Device ](/timer_subsystem/tick-device-layer.html#c8670) |
| 2022-08-23 | CXK | @crash：ldrex本身是一个原子读指令，如果在这个期间这块内存被修改了，那么，就算醒来以后执行的strex指令也是会失败，也会重新跳转到ldrex，这段代码利用了原子操作的机制来保证不会出错。 | [Linux内核同步机制之（五）：Read/Write s](/kernel_synchronization/rw-spinlock.html#c8669) |
| 2022-08-10 | orangeboyye | @yanl1229：有6位可用，目前只用了3位。 | [Linux内核同步机制之（八）：mutex](/kernel_synchronization/504.html#c8668) |
| 2022-08-10 | mingtian | @Liu：后面的原子操作并没有关闭中断，只是通过局部检视和全局检视两种实现了原子操作 | [Linux内核同步机制之（一）：原子操作](/kernel_synchronization/atomic.html#c8667) |
| 2022-08-09 | yanl1229 | 2. 由于task struct地址是L1_CACHE_BYTES对齐的，因此这个成员的有若干的LSB可以被用于标记状态（在ARM64平台上，L1_CACHE_BYTES是64字节，因此LSB 6-bit会用于保存mutex状态信息
 
 这句话是不是描述错误了，我看4.19的内核是: 
 static inline … | [Linux内核同步机制之（八）：mutex](/kernel_synchronization/504.html#c8666) |
| 2022-08-08 | bsp | @yui：linux作为虚拟机VM运行时，就要配置成virtual timer；
 EL2的hypervisor使用physical timer；
 一般virtual_time = physical_timer - offset;
 offset(CNTVOFF寄存器)由hypervisor调整，比如VM_linux… | [Linux时间子系统之（十七）：ARM generic ](/timer_subsystem/armgeneraltimer.html#c8665) |
| 2022-08-08 | orangeboyye | 原文：“如果以NICE值为20计算的话，只需要8年左右时间”，应该是-20，少写个负号 | [CFS调度器（6）-总结](/process_management/452.html#c8664) |
| 2022-08-05 | fanqirong660 | @matchchen：跟回帖有同样的疑惑。
 之前ARM32上，boot_jump_linux传的fdt_addr以及在uboot里解析fdt得到的ramdisk等信息，都填在bootm_headers_t结构体里传给kernel了。
 
 但ARM64上，boot_jump_linux只传fdt_addr。那是不是只… | [ARM64的启动过程之（一）：内核第一个脚印](/armv8a_arch/arm64_initialize_1.html#c8663) |
| 2022-08-05 | Ethan | @wowo：这句话从我中学到现在还没改，建议把这些用的评论置顶，这样有疑惑的朋友能第一时间看到大佬们的讨论 | [Linux设备模型(1)_基本概念](/device_model/13.html#c8662) |
| 2022-08-02 | eexplorer | crash> dma_pool ffff9d0fa45f4c00 -x
 struct dma_pool {
 ...
   pools = {
     next = 0xdead000000000100, 
     prev = 0xdead000000000200
   }
 }
 
 从dma_pool.po… | [mellanox的网卡故障分析](/linux_kenrel/485.html#c8661) |
| 2022-07-29 | zxl | @zxl：大老们，
    请帮助解惑以下。 谢谢 | [Linux内核中的GPIO系统之（3）：pin cont](/gpio_subsystem/pin-controller-driver.html#c8660) |
| 2022-07-29 | zxl | serial@50000000 { 
         ……
         pinctrl-names = "default";
         pinctrl-0 = <0x2 0x3>;
     };
 该serial device只定义了一个state就是default，对应pinctrl-0属性定义。p… | [Linux内核中的GPIO系统之（3）：pin cont](/gpio_subsystem/pin-controller-driver.html#c8659) |
| 2022-07-28 | donbear | 我想我明白了.
 
 *_avg 就是在 [1024us, 1024us, ...] 这个时间序列的对应指标统计的加权平均.
 *_avf 的分母完全是由它的数学定义推导而来的,其原始定义其实就是一个 Exponential Moving Average，分母的推导可以看http://en.wikipedia.org/… | [PELT算法浅析](/process_management/pelt.html#c8658) |
| 2022-07-27 | Toni | @秋暮离：同样的问题 | [Linux DMA Engine framework(3](/linux_kenrel/dma_controller_driver.html#c8657) |
| 2022-07-26 | dream | 既然能控制 GPIO ，模拟 UART TX 不更爽? 波特率可以搞低一点，如 9600 一次痛苦百次爽，哈哈。 | [通过点亮LED的方法调试嵌入式代码](/soft/debug_using_led.html#c8656) |
| 2022-07-26 | smallfish | @linuxer：大佬，你说利用 globa count来统计各个cpu 本地的累加值，这个好理解，但是我的操作不是++或者--， 我要对这个count 赋值，比如说count=0，  那这个是不是还得进行同步。 | [Linux内核同步机制之（二）：Per-CPU变量](/kernel_synchronization/per-cpu.html#c8655) |
| 2022-07-26 | 江南王公子 | 有个问题，why cannot send English content directly ? | [新技能get: 订阅Linux内核邮件列表](/linux_application/lkml.html#c8654) |
| 2022-07-26 | 江南王公子 | A级TBB | [新技能get: 订阅Linux内核邮件列表](/linux_application/lkml.html#c8653) |
| 2022-07-26 | Redsky | @donbear：这个问题我是这么理解的，几何最大值，表征的是在衰减期间内，每一个us内se都处于running/runnable状态的sum，实际上也可以理解为某一时刻load在load sum计算中衰减到0的时间，也就是衰减周期的us数量。sum/time，计算出来的是avg。
 
 如果理解错了，请博主指正。 | [PELT算法浅析](/process_management/pelt.html#c8652) |
| 2022-07-25 | 王传琪 | @王传琪：纠正上面评论，在注册pinctrl设备的时候 pinctrl_register 函数会调用 pinctrl_enable 里面的 pinctrl_claim_hogs 会设置引脚默认状态，这样看是会设置引脚默认状态的 | [Linux内核中的GPIO系统之（3）：pin cont](/gpio_subsystem/pin-controller-driver.html#c8651) |
| 2022-07-23 | dream | 我也是这么认为的：有静态变量就意味着函数不可重入，不可重入的函数，只要有可能出现并发调用，都应该加上锁进行保护。 | [spin_lock最简单用法。](/164.html#c8650) |
| 2022-07-22 | dream | linuxer:
 
 看到这段话，有些不理解，还请解惑，非常感谢。
 
 "A在进入临界区之前获取了spin lock，同样的，在A访问共享资源R的过程中发生了中断，中断唤醒了沉睡中的，优先级更高的B，B在访问临界区之前仍然会试图获取spin lock，这时候由于A进程持有spin lock而导致B进程进入了永久的s… | [Linux内核同步机制之（四）：spin lock](/kernel_synchronization/spinlock.html#c8649) |
| 2022-07-22 | zach | 非常感谢能写出这么清晰的文章，就是有个疑问，按照文中的描述，cache根据自身的size划分为多个cache line，每个cache line中存储的一段主存中的数据，tag array是储存在什么地方的呢，按我的理解应该是存储在cache中的，如果是这样是否可以理解为cache的内容是由tag array和data… | [浅谈Cache Memory](/memory_management/458.html#c8648) |
| 2022-07-21 | 王传琪 | @王传琪：这几天加打印信息看了一下，找不到设备返回ENODEV，但pinctrl_bind_pins只有在出现EPROBE_DEFER和EINVAL才会返回错误，其他错误都被忽略了，直接返回0，然后继续进行really_probe剩下的流程，只不过不会设置pin而已。那这样pinctrl里面添加的默认设置看来是不会初始… | [Linux内核中的GPIO系统之（3）：pin cont](/gpio_subsystem/pin-controller-driver.html#c8647) |
| 2022-07-20 | xyy | @伊斯科明：有通知和没通知的区别 | [统一设备模型：kobj、kset分析](/device_model/421.html#c8646) |
| 2022-07-20 | wenxl | "一个entity对系统负载的贡献可以根据该实体处于runnable状态（正在CPU上运行或者等待cpu调度运行）的时间进行计算"
 ---------------------------------------------------------------------------------------------… | [CFS调度器（4）-PELT(per entity lo](/process_management/450.html#c8645) |
| 2022-07-17 | donbear | 感谢分享，很精彩啊。
 
 有一个疑问希望能得到博主的解答。
 
 在通过 *sum 计算 *avg 的时候，为什么是除以几何级数的最大值？
 按照linux中源码注释以及各处看到的公式，这里貌似除1024就可以了？:(
 
 static __always_inline void
 ___update_load_av… | [PELT算法浅析](/process_management/pelt.html#c8644) |
| 2022-07-15 | 王传琪 | @王传琪：感觉前面描述的有点问题，改一下。 
     我在看pinctrl_register注册的时候有个疑问，就是pinctrl driver也是一个platform driver，走的标准的driver注册流程。会进入到really_probe这个函数，然后也会调用pinctrl_bind_pins，去绑定和设置… | [Linux内核中的GPIO系统之（3）：pin cont](/gpio_subsystem/pin-controller-driver.html#c8643) |
| 2022-07-15 | 王传琪 | 各位大佬好！
 
     我在看pinctrl_register注册的时候有个疑问，就是pinctrl子系统也是一个platform driver，这样他也是走的标准的driver注册流程。会进入到really_probe这个函数，然后也会调用pinctrl_bind_pins，去绑定和设置默认io，但这个时候pin… | [Linux内核中的GPIO系统之（3）：pin cont](/gpio_subsystem/pin-controller-driver.html#c8642) |
| 2022-07-12 | qp123 | 谢谢你这么无私的人 | [u-boot启动流程分析(2)_板级(board)部分](/u-boot/boot_flow_2.html#c8641) |
| 2022-07-06 | 点灯大师 | 怒赞 | [关于蜗窝](/about.html#c8640) |
| 2022-07-04 | lamb | @jackzhous：kernel待机、睡眠过程看这篇入门，系统睡眠的入口在这里
 /pm_subsystem/autosleep.html | [Linux电源管理(15)_PM OPP Interfa](/pm_subsystem/pm_opp.html#c8639) |
| 2022-07-04 | 雁落 | 那张uboot架构图是你自己理解画出来的吗，把我惊住了 | [u-boot启动流程分析(1)_平台相关部分](/u-boot/boot_flow_1.html#c8638) |
| 2022-07-01 | ctwillson | 一直没理解在抓到的 systrace 中有个
 <idle>-0     (-----) [002] .n.1 39203.759393: cpu_idle: state=4294967295 cpu_id=2
 这种 c-state 代表的是什么含义？ | [Linux cpuidle framework(4)_m](/pm_subsystem/cpuidle_menu_governor.html#c8637) |
| 2022-06-30 | 三变 | 每次来都有新的收获，从uboot学到kernel wowo这都有我想要的 纯粹的技术原理 | [留言板](/message_board.html#c8636) |
| 2022-06-30 | wate | @albert：如果只从保持高优先级角度看的话，那只有让中断处理程序处于中断上下文时有最高优先级了，使用IRQF_NOTHREAD在request_thread_irq()注册时明确指定不线程化应该是可以满足高优先级的问题。否则，线程化之后会被内核高优先级线程欺负的。 | [Linux kernel中断子系统之（五）：驱动申请中断](/irq_subsystem/request_threaded_irq.html#c8635) |
| 2022-06-28 | DonGe | Pinctrl子系统就给我看晕了 | [Linux内核中的GPIO系统之（3）：pin cont](/gpio_subsystem/pin-controller-driver.html#c8634) |
| 2022-06-26 | running | start.s应该不是运行在cortex M3上的，很多ROM code会运行在AArch32模式，比如高通等，hikey应该也是一样，AP上电工作在AArch32，通过warm reset执行BL2时，切换为AArch64. | [基于Hikey的"Boot from USB"调试](/x_project/hikey_usb_boot.html#c8633) |
| 2022-06-25 | focus | 清晰。 | [页面回收的基本概念](/memory_management/page_reclaim_basic.html#c8632) |
| 2022-06-24 | solar | @海：您好，请问这个资料还在吗，百度盘的链接失效了 | [Linux电源管理(11)_Runtime PM之功能描](/pm_subsystem/rpm_overview.html#c8631) |
| 2022-06-16 | jarvis | @linuxer：我看wakeup task的代码，如果任务原先的cpu和当前选择的select cpu不同的话，会走到migrate_task_rq_fair，其会做se->vruntime -= min_vruntime，即会减去任务原先所在cpu的min_vruntime；这就相当于是在唤醒的时候减去min_vr… | [CFS调度器（2）-源码解析](/process_management/448.html#c8630) |
| 2022-06-14 | cocoHero | 请教一下大神，   BLE广播的时候，有没有限制scaning的数目呢？ 比如passive状态的scanning实体，是不是可以有无穷多个？ 
 
 如果是需要有回复的scaning实体，应该是链接数目达到上限后，就不能再响应ADV_IND/CONNECT_REQ了吗？ | [蓝牙协议分析(5)_BLE广播通信相关的技术分析](/bluetooth/ble_broadcast.html#c8629) |
| 2022-06-14 | haifan | @wowo：还有芯片设计时成本允许的情况下加大rx fifo, 还有就是使用4线串口，使用硬件流控的方式。 | [Linux serial framework(1)_概述](/comm/serial_overview.html#c8628) |
| 2022-06-08 | Liu | 这里有一个疑惑，如果关闭中断后由外部中断触发怎么办？是不是说如果系统要求很高的时候这种保证原子的方法不太实用呢 | [Linux内核同步机制之（一）：原子操作](/kernel_synchronization/atomic.html#c8627) |
| 2022-06-06 | 十岁卖切糕丶 | 能基于kernel5.4以上的内核，用gki的方式写个添加节点的文章吗 | [Linux power supply class(1)_](/pm_subsystem/psy_class_overview.html#c8626) |
| 2022-06-05 | irreallich | @benjoying：其实对于目前的很多开发者来说,反倒是直接折腾硬件更加简便
 做控制器开发很多资深工程师大多经历过单片机,rots,到linux的过程,对linux的dmaengine系统并不熟, 但是因为以前的经验, 对dma控制器的逻辑很熟, 直接从芯片手册操作寄存器的来实现dma功能的速度更快 | [Linux DMA Engine framework(2](/linux_kenrel/dma_engine_api.html#c8625) |
| 2022-06-02 | 观察者 | 2014-5-23 发的博客，到现在2022-6-2，依旧对学习ble的新手来说具有很大的学习价值，感谢蜗蜗！ | [蓝牙协议分析(1)_基本概念](/bluetooth/bt_overview.html#c8624) |
| 2022-06-01 | ctwillson | 之后有没有分享嵌入式设备的调度，比如 EAS WALT... | [PELT算法浅析](/process_management/pelt.html#c8623) |
| 2022-05-30 | 曾尚文 | 好好学习，天天向上 | [支持与合作](/support_us.html#c8622) |
| 2022-05-24 | 摩斯电码 | SCHED_IDLE属于fair_sched_class，而不是idle_sched_class | [CFS调度器（1）-基本原理](/process_management/447.html#c8621) |
| 2022-05-24 | linuxer | @gavin：因为HIGHMEM memory没有进行线性映射，所以没有虚拟地址呀。 | [Dynamic DMA mapping Guide](/memory_management/DMA-Mapping-api.html#c8620) |
| 2022-05-19 | gavin | 请问这个地方说：。dma_map_single函数在进行DMA mapping的时候使用的是CPU指针（虚拟地址），这样就导致该函数有一个弊端：不能使用HIGHMEM memory进行mapping。 这个为啥不能呢？谢谢 | [Dynamic DMA mapping Guide](/memory_management/DMA-Mapping-api.html#c8619) |
| 2022-05-19 | hw07 | 第一张图是不是画错了？下面的BITLINE 应该改/BITLINE, output 也应该为/output | [DRAM 原理 2 ：DRAM Memory Organ](/basic_tech/309.html#c8618) |
| 2022-05-19 | hw07 | output 和/output 那个是输出？ | [DRAM 原理 1 ：DRAM Storage Cell](/basic_tech/307.html#c8617) |
| 2022-05-18 | 明天 | 有两种情况会恢复：1退出中断的时候，因为会恢复cpsr寄存器；2、软中断soft_irq中会打开中断 | [Linux kernel的中断子系统之（六）：ARM中断](/irq_subsystem/irq_handler.html#c8616) |
| 2022-05-16 | caid2012 | @wowo：第一、二部分似乎描述Android搞了两个wakelocks，一个销声匿迹，一个基于kernel的wakeup events框架；且新的wakelocks是kernel/power/wakelock.c
 
 第三节又描述了kernel的wakelocks机制；并且与Android的wakelocks机制作… | [Linux电源管理(9)_wakelocks](/pm_subsystem/wakelocks.html#c8615) |
| 2022-05-09 | bsp | @江南书生：内存之上还有cache，cache还有L1/L2/L3。很多时候cpu会从DDR 一次性load一个cacheline的内存（或数据或指令），然后CPU基于cache工作即可，此时就不需要DDR； | [Linux DMA Engine framework(1](/linux_kenrel/dma_engine_overview.html#c8614) |
| 2022-05-08 | y | 精彩的分析，希望有更多用例分享。 | [关于numa loadbance的死锁分析](/linux_kenrel/482.html#c8613) |
| 2022-05-06 | ora | @victor：有同样的困惑，通过/proc/pagetypeinfo来看，CMA类型最大的order也是10(4M)，怎么做的更大连续内存的分配？ | [CMA模块学习笔记](/memory_management/cma.html#c8612) |
| 2022-05-05 | eshin | @David：您提问题的时间是2018年,这时候发布的规格书是4.2.这里只讨论device支持privacy mode的情况,应该是这样:
 1. initiator address只能是RPA(resolvable private address)地址.具体可见蓝牙核心协议core4.2及以上 [Vol 6, Pa… | [蓝牙协议分析(6)_BLE地址类型](/bluetooth/ble_address_type.html#c8611) |
| 2022-04-29 | orangeboyye | @linuxer：非常感谢，之前加过你的微信，微信聊。 | [Linux内核同步机制之（七）：RCU基础](/kernel_synchronization/rcu_fundamentals.html#c8610) |
| 2022-04-29 | 明天 | @太空的树懒：讲的很清楚了  （4）很多异常处理的代码返回的时候都是使用了stack相关的操作，这里没有。“movs    pc, lr ”指令除了字面上意思（把lr的值付给pc），还有一个隐含的操作（movs中‘s’的含义）：把SPSR copy到CPSR，从而实现了模式的切换。 模式的切换是靠修改cpsr寄存器实现… | [Linux kernel的中断子系统之（六）：ARM中断](/irq_subsystem/irq_handler.html#c8609) |
| 2022-04-29 | linuxer | @orangeboyye：这位同学，有没有兴趣来OPPO搞内核优化，O(∩_∩)O
 要不要加个微信详聊一下，哈哈。 | [Linux内核同步机制之（七）：RCU基础](/kernel_synchronization/rcu_fundamentals.html#c8608) |
| 2022-04-29 | orangeboyye | @luke：两个写者不能同时执行，因为一个写者要基于另一个写者的结果去操作才行，否则就会丢失一个写者的操作。
 假设RCU保护的是int * p = &i，i=1，两个写者的操作都是要i++，按照你的逻辑操作，最后i==2，和预期的i==3不符，丢失了一个写者的操作。 | [Linux内核同步机制之（七）：RCU基础](/kernel_synchronization/rcu_fundamentals.html#c8607) |
| 2022-04-28 | raceant | @wahaha02：hwspinlock 是怎样实现的呢？ | [Atomic operation in aarch64](/armv8a_arch/492.html#c8606) |
| 2022-04-28 | Gonglja | @wolf2blood：uboot中 添加对扁平化设备树的支持，CONFIG_OF_LIBFDT，然后机器码传递0xffffffff即可。 | [Device Tree（一）：背景介绍](/device_model/why-dt.html#c8605) |
| 2022-04-28 | orangeboyye | @sgy1993：死锁的意思是A等B，同时B也在等A，等的不一定是锁啊，只要是在等待就行。main先调用func1，再调用func2，func2就是在等func1执行完才能执行啊，这个在逻辑上也是等啊，因为如果func1一直卡在那执行不完，func2就不可能执行。 | [Concurrency Managed Workqueu](/irq_subsystem/cmwq-intro.html#c8604) |
| 2022-04-28 | orangeboyye | @sgy1993：文中的意思是说在work A中要等待work B的执行结果，但是不碰巧，work A 和B被放到了同一个CPU上，而且A在前，那么A就会阻塞等待B，可是B要等A执行完之后才能执行，因此产生了A等B，B等A，相互等待，就是死锁啊。 | [Concurrency Managed Workqueu](/irq_subsystem/cmwq-intro.html#c8603) |
| 2022-04-28 | orangeboyye | @张飞：没有说反，你仔细看代码，这三个条件不是or的关系，是and的关系，第一个成立了才会去看第二个，第二个成立了才会去看第三个，第一个条件是没有在冻结，如果不成立就是在冻结，整个表达式为false，后面的就不看了，if子语句不执行，下面的语句是try_to_freeze，正好执行冻结啊。第二代条件同理。当三个条件都成… | [Concurrency Managed Workqueu](/irq_subsystem/workqueue.html#c8602) |
| 2022-04-28 | orangeboyye | @小学生：如果你这样写代码就会导致少一个work处理，所以不能这么写代码，你应该每次都创建一个新的work来执行，不要复用work。当然我遇到过复用work的，它的逻辑是这么写的，把要处理的事情放到另一个list上，work遍历那个list处理事情，scheddule_work在这里是的作用就是如果work没在运行就唤… | [Concurrency Managed Workqueu](/irq_subsystem/workqueue.html#c8601) |
| 2022-04-28 | orangeboyye | @wangyunqian：你那个不是suspend to ram吧，suspend to disk才会从bootrom开始执行，相当于是关机重启了，重启时会加载disk上存的东西，恢复现场。 | [中断唤醒系统流程](/irq_subsystem/irq_handle_procedure.html#c8600) |
| 2022-04-28 | abcdefg1324 | 赞！实际移植才能理解深刻，这种尝试也挺有意义 | [PELT算法浅析](/process_management/pelt.html#c8599) |
| 2022-04-28 | jackzhous | 时间有点久，不知道博主还能不能回复我；初学者，有个疑问，按照大学学单片机时候的理解，电源管理这些待机、睡眠最终在硬件上的体现是往硬件提供的寄存器写值，或者往芯片某个引脚拉高、拉低电平，从而硬件就变为待机、睡眠等状态，是这样理解吗？如果是在kernel代码里面哪里有代码可以体现呢？ | [Linux电源管理(15)_PM OPP Interfa](/pm_subsystem/pm_opp.html#c8598) |
| 2022-04-27 | orangeboyye | 用发行版的config有个问题，就是发行版为了在各种机器上运行配置了大量的ko，导致编译时间会非常长。其实内核已经给我们提供了一个方法 make localmodconfig，会根据系统现在的状态只配置目前加载的ko，这样编译时间就会非常快，在我的电脑上virtualbox虚拟机里4核编译不到30分钟就编译好了。 | [Debian8 内核升级实验](/linux_application/debian8-upgrade-kernel.html#c8597) |
| 2022-04-26 | orangeboyye | @哈默：这个系列的文章逻辑还是非常清晰的，只不过不适合新人，要有很深厚的内核基础才行，对内核只有一般性了解的来说读起来都非常吃力，有很多概念都没有解释都是直接假设你已经懂了的，比如调度、PM相关的知识。 | [Linux时间子系统之（十四）：tick broadca](/timer_subsystem/tick-broadcast-framework.html#c8596) |
| 2022-04-26 | evilpan | 赞，期待后续 | [schedutil governor情景分析](/process_management/schedutil_governor.html#c8595) |
| 2022-04-26 | linuxer | @orangeboyye：应该是，但时间过于久远了，现在都忘记要写什么了。 | [Linux时间子系统之（四）：timekeeping](/timer_subsystem/timekeeping.html#c8594) |
| 2022-04-25 | orangeboyye | 七 2 (4)最后一句：如果delta_delta大于2秒，突然结束了，是不是少写了半句话？ | [Linux时间子系统之（四）：timekeeping](/timer_subsystem/timekeeping.html#c8593) |
| 2022-04-22 | linuxer | @zzz：的确如你所言，理论需要结合实际。不过，我目前的工作就是做内核优化的，所以不缺实践，哈哈^_^
 有兴趣来做内核优化实践的话可以联系我，微信是Linuxer-at-wowo | [PELT算法浅析](/process_management/pelt.html#c8592) |
| 2022-04-20 | zzz | 文章写的很赞！想问下作者调度和负载均衡这块代码是如何学进去的，因为调度并不像实际一个设备驱动或者其他模块代码那么容易上手和实践，这里如何和实践相结合呢。 | [PELT算法浅析](/process_management/pelt.html#c8591) |
| 2022-04-20 | jimi | @wowo：子里行间都能感觉到wowo的真诚，对自己、对别人、对技术都是这样，敬佩！ | [支持者列表](/support_list.html#c8590) |
| 2022-04-19 | llp | @daiyinger：请问你这个物理地址在mmu enable 之后，是如何映射的 | [ARM64的启动过程之（四）：打开MMU](/armv8a_arch/turn-on-mmu.html#c8589) |
| 2022-04-18 | bsp | @呜啦啦：是的，我也觉得seqlock不适合保护指针。 | [Linux内核同步机制之（六）：Seqlock](/kernel_synchronization/seqlock.html#c8588) |
| 2022-04-14 | shu | @慢慢想：上述耗时的问题确定了吗？ | [Linux设备模型(3)_Uevent](/device_model/uevent.html#c8587) |
| 2022-04-11 | Franky_Pan | 感谢感谢。学习了~ | [支持与合作](/support_us.html#c8586) |

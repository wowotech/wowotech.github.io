---
title: "Linux kernel debug技巧----开启DEBUG选项"
date: 2016-11-01T19:39:29+08:00
url: "/linux_application/kernel_debug_enable.html"
gid: "348"
emlog_type: "blog"
summary: "\r\n\tkernel的source code中有很多使用pr_debug/dev_dbg输出的日志信息（例如device \r\ntree解析的代码，drivers/of/fdt.c）。默认情况下，kernel不会将这些日志输出到控制台上，除非：\r\n\r\n\r\n\t\r\n\t\t1）开启了DEBUG宏，并且\r\n\t\r\n\t\r\n\t\t2）kernel printk的默认日志级别大于7\r\n\t\r\n\r\n\r\n\t看似简单，不过我相信"
author: "wowo"
category: "Linux应用技巧"
category_alias: "linux_application"
tags: ["debug", "Linux", "Kernel", "printk", "pr_debug", "dev_dbg"]
views: 48979
comment_count: 8
aliases:
  - "/linux_application/348.html"
  - "/348.html"
---

kernel的source code中有很多使用pr\_debug/dev\_dbg输出的日志信息（例如device tree解析的代码，drivers/of/fdt.c）。默认情况下，kernel不会将这些日志输出到控制台上，除非：

> 1）开启了DEBUG宏，并且
>
> 2）kernel printk的默认日志级别大于7

看似简单，不过我相信每个人都问过这样的问题（不管是问自己还是问别人，特别是在调试kernel启动过程的时候，例如device tree的匹配、device probe等）：怎么开启DEBUG选项？

之所以有这篇短文，是因为我也问过（不止一次），于是就记录如下：

1）开启了DEBUG宏

其实开启DEBUG宏的方法很简单，在需要pr\_debug/dev\_dbg输出的模块开头，直接#define DEBUG即可，kernel中有一个例子：

> /\* init/main.c \*/
>
> #define DEBUG /\* Enable initcall\_debug \*/

不过这种方法有个缺点：我们必须准确的知道需要debug那个C文件，如果想大网撒鱼（例如，想debug为什么新修改的DTS文件没有起作用，而又对kernel fdt的代码不是很熟悉），就麻烦了。这里我给一个大杀器：在编译kernel的时候，通过KCFLAGS直接传递，这样可以全局生效，如下（以本站的“[X Project](/sort/x_project)”为例）：

> diff --git a/Makefile b/Makefile   
> index 0835b1c..59625f4 100644   
> --- a/Makefile   
> +++ b/Makefile   
> @@ -83,7 +83,7 @@ kernel-config:   
> kernel:   
> mkdir -p $(KERNEL\_OUT\_DIR)   
> make -C $(KERNEL\_DIR) CROSS\_COMPILE=$(CROSS\_COMPILE) KBUILD\_OUTPUT=$(KERNEL\_OUT\_DIR) ARCH=$(BOARD\_ARCH) $(KERNEL\_D   
> - make -C $(KERNEL\_DIR) CROSS\_COMPILE=$(CROSS\_COMPILE) KBUILD\_OUTPUT=$(KERNEL\_OUT\_DIR) ARCH=$(BOARD\_ARCH) $(KERNEL\_T   
> + make -C $(KERNEL\_DIR) CROSS\_COMPILE=$(CROSS\_COMPILE) KBUILD\_OUTPUT=$(KERNEL\_OUT\_DIR) KCFLAGS=-DDEBUG ARCH=$(BOARD\_

2）设置kernel printk的默认日志级别为8

修改printk的默认日志级别的方法有多种，例如直接修改printk.c(新kernel为printk.h)中的CONSOLE\_LOGLEVEL\_DEFAULT宏定义。不过修改kernel原生代码的方式稍显粗暴，我们还有优雅一些的手段，例如通过命令行参数的loglevel变量传递，如下：

> diff --git a/arch/arm64/configs/xprj\_defconfig b/arch/arm64/configs/xprj\_defconfig   
> index 5d0d591..9335d3f 100644   
> --- a/arch/arm64/configs/xprj\_defconfig   
> +++ b/arch/arm64/configs/xprj\_defconfig   
> @@ -320,7 +320,7 @@ CONFIG\_FORCE\_MAX\_ZONEORDER=11   
> #   
> # Boot options   
> #   
> -CONFIG\_CMDLINE="earlycon=owl\_serial"   
> +CONFIG\_CMDLINE="earlycon=owl\_serial loglevel=8"   
> CONFIG\_CMDLINE\_FORCE=y   
> # CONFIG\_EFI is not set

3）修改完之后，编译并启动kernel看看效果吧（是不是很爽？）

> Starting kernel ...
>
> flushing dcache successfully.   
> [ 0.000000] Booting Linux on physical CPU 0x0   
> [ 0.000000] Linux version 4.6.0-rc5+ (pengo@ubuntu) (gcc version 4.8.3 20131202 (prerelease) (crosstool-NG linaro-1.13.1-4.8-2013.12 - Linaro GCC 2013.11) ) #17 SMP Tue Nov 1 03:52:32 PDT 2016   
> [ 0.000000] Boot CPU: AArch64 Processor [410fd032]   
> [ 0.000000] earlycon: owl\_serial0 at I/O port 0x0 (options '')   
> [ 0.000000] bootconsole [owl\_serial0] enabled   
> [ 0.000000] On node 0 totalpages: 524288   
> [ 0.000000] DMA zone: 8192 pages used for memmap   
> [ 0.000000] DMA zone: 0 pages reserved   
> [ 0.000000] DMA zone: 524288 pages, LIFO batch:31   
> [ 0.000000] -> unflatten\_device\_tree()   
> [ 0.000000] Unflattening device tree:   
> [ 0.000000] magic: d00dfeed   
> [ 0.000000] size: 00001000   
> [ 0.000000] version: 00000011   
> [ 0.000000] size is cb0, allocating...   
> [ 0.000000] unflattening ffffffc07ffed1c8...   
> [ 0.000000] fixed up name for ->   
> [ 0.000000] fixed up name for memory -> memory   
> [ 0.000000] fixed up name for chosen -> chosen   
> [ 0.000000] fixed up name for interrupt-controller@e00f1000 -> interrupt-controller   
> [ 0.000000] fixed up name for timer -> timer   
> [ 0.000000] <- unflatten\_device\_tree()   
> [ 0.000000] Failed to find device node for boot cpu   
> [ 0.000000] missing boot CPU MPIDR, not enabling secondaries   
> [ 0.000000] mask of set bits 0x0   
> [ 0.000000] MPIDR hash: aff0[0] aff1[8] aff2[16] aff3[32] mask[0x0] bits[0]   
> [ 0.000000] percpu: Embedded 14 pages/cpu @ffffffc07ffdd000 s28032 r0 d29312 u57344   
> [ 0.000000] pcpu-alloc: s28032 r0 d29312 u57344 alloc=14\*4096   
> [ 0.000000] pcpu-alloc: [0] 0   
> [ 0.000000] Detected VIPT I-cache on CPU0   
> [ 0.000000] Built 1 zonelists in Zone order, mobility grouping on. Total pages: 516096   
> [ 0.000000] Kernel command line: earlycon=owl\_serial loglevel=8   
> [ 0.000000] doing Booting kernel, parsing ARGS: 'earlycon=owl\_serial loglevel=8'   
> [ 0.000000] doing Booting kernel: earlycon='owl\_serial'   
> [ 0.000000] doing Booting kernel: loglevel='8'   
> [ 0.000000] PID hash table entries: 4096 (order: 3, 32768 bytes)   
> [ 0.000000] Dentry cache hash table entries: 262144 (order: 9, 2097152 bytes)   
> [ 0.000000] Inode-cache hash table entries: 131072 (order: 8, 1048576 bytes)   
> [ 0.000000] software IO TLB [mem 0x79cb3000-0x7dcb3000] (64MB) mapped at [ffffffc079cb3000-ffffffc07dcb2fff]   
> [ 0.000000] Memory: 1993604K/2097152K available (1032K kernel code, 78K rwdata, 128K rodata, 120K init, 201K bss, 103548K reserved, 0K cma-reserved)   
> [ 0.000000] Virtual kernel memory layout:   
> [ 0.000000] modules : 0xffffff8000000000 - 0xffffff8008000000 ( 128 MB)   
> [ 0.000000] vmalloc : 0xffffff8008000000 - 0xffffffbdbfff0000 ( 246 GB)   
> [ 0.000000] .text : 0xffffff8008080000 - 0xffffff8008182000 ( 1032 KB)   
> [ 0.000000] .rodata : 0xffffff8008182000 - 0xffffff80081a3000 ( 132 KB)   
> [ 0.000000] .init : 0xffffff80081a3000 - 0xffffff80081c1000 ( 120 KB)   
> [ 0.000000] .data : 0xffffff80081c1000 - 0xffffff80081d4800 ( 78 KB)   
> [ 0.000000] fixed : 0xffffffbffe7fd000 - 0xffffffbffec00000 ( 4108 KB)   
> [ 0.000000] PCI I/O : 0xffffffbffee00000 - 0xffffffbfffe00000 ( 16 MB)   
> [ 0.000000] memory : 0xffffffc000000000 - 0xffffffc080000000 ( 2048 MB)   
> [ 0.000000] SLUB: HWalign=64, Order=0-3, MinObjects=0, CPUs=1, Nodes=1   
> [ 0.000000] Hierarchical RCU implementation.   
> [ 0.000000] Build-time adjustment of leaf fanout to 64.   
> [ 0.000000] RCU restricting CPUs from NR\_CPUS=64 to nr\_cpu\_ids=1.   
> [ 0.000000] RCU: Adjusting geometry for rcu\_fanout\_leaf=64, nr\_cpu\_ids=1   
> [ 0.000000] NR\_IRQS:64 nr\_irqs:64 0   
> [ 0.000000] of\_irq\_init: init /interrupt-controller@e00f1000 (ffffffc07ffed800), parent (null)   
> [ 0.000000] OF: \*\* translation for device /interrupt-controller@e00f1000 \*\*   
> [ 0.000000] OF: bus is default (na=2, ns=2) on /   
> [ 0.000000] OF: translating address: 00000000 e00f1000   
> [ 0.000000] OF: reached root node   
> [ 0.000000] OF: \*\* translation for device /interrupt-controller@e00f1000 \*\*   
> [ 0.000000] OF: bus is default (na=2, ns=2) on /   
> [ 0.000000] OF: translating address: 00000000 e00f2000   
> [ 0.000000] OF: reached root node   
> [ 0.000000] OF: \*\* translation for device /interrupt-controller@e00f1000 \*\*   
> [ 0.000000] OF: bus is default (na=2, ns=2) on /   
> [ 0.000000] OF: translating address: 00000000 e00f2000   
> [ 0.000000] OF: reached root node   
> [ 0.000000] irq: Added domain (null)   
> [ 0.000000] of\_irq\_parse\_one: dev=/timer, index=0   
> [ 0.000000] intspec=1 intlen=12   
> [ 0.000000] intsize=3 intlen=12   
> [ 0.000000] of\_irq\_parse\_raw: /interrupt-controller@e00f1000:00000001,0000000d,00000f08   
> [ 0.000000] of\_irq\_parse\_raw: ipar=/interrupt-controller@e00f1000, size=3   
> [ 0.000000] -> addrsize=0   
> [ 0.000000] -> got it !   
> [ 0.000000] of\_irq\_parse\_one: dev=/timer, index=1   
> [ 0.000000] intspec=1 intlen=12   
> [ 0.000000] intsize=3 intlen=12   
> [ 0.000000] of\_irq\_parse\_raw: /interrupt-controller@e00f1000:00000001,0000000e,00000f08   
> [ 0.000000] of\_irq\_parse\_raw: ipar=/interrupt-controller@e00f1000, size=3   
> [ 0.000000] -> addrsize=0   
> [ 0.000000] -> got it !   
> [ 0.000000] of\_irq\_parse\_one: dev=/timer, index=2   
> [ 0.000000] intspec=1 intlen=12   
> [ 0.000000] intsize=3 intlen=12   
> [ 0.000000] of\_irq\_parse\_raw: /interrupt-controller@e00f1000:00000001,0000000b,00000f08   
> [ 0.000000] of\_irq\_parse\_raw: ipar=/interrupt-controller@e00f1000, size=3   
> [ 0.000000] -> addrsize=0   
> [ 0.000000] -> got it !   
> [ 0.000000] of\_irq\_parse\_one: dev=/timer, index=3   
> [ 0.000000] intspec=1 intlen=12   
> [ 0.000000] intsize=3 intlen=12   
> [ 0.000000] of\_irq\_parse\_raw: /interrupt-controller@e00f1000:00000001,0000000a,00000f08   
> [ 0.000000] of\_irq\_parse\_raw: ipar=/interrupt-controller@e00f1000, size=3   
> [ 0.000000] -> addrsize=0   
> [ 0.000000] -> got it !   
> [ 0.000000] Architected cp15 timer(s) running at 24.00MHz (phys).   
> [ 0.000000] clocksource: arch\_sys\_counter: mask: 0xffffffffffffff max\_cycles: 0x588fe9dc0, max\_idle\_ns: 440795202592 ns   
> [ 0.000031] sched\_clock: 56 bits at 24MHz, resolution 41ns, wraps every 4398046511097ns   
> [ 0.007999] Registered 0xffffff800816bf78 as sched\_clock source   
> [ 0.013906] Calibrating delay loop (skipped), value calculated using timer frequency.. 48.00 BogoMIPS (lpj=96000)   
> [ 0.024093] pid\_max: default: 4096 minimum: 301   
> [ 0.028687] Mount-cache hash table entries: 4096 (order: 3, 32768 bytes)   
> [ 0.035281] Mountpoint-cache hash table entries: 4096 (order: 3, 32768 bytes)   
> [ 0.042468] kobject: 'fs' (ffffffc079802c00): kobject\_add\_internal: parent: '', set: ''   
> [ 0.051687] No CPU information found in DT   
> [ 0.055499] CPU0: cluster 0 core 0 thread -1 mpidr 0x00000080000000   
> [ 0.061718] ASID allocator initialised with 65536 entries   
> [ 0.067687] Brought up 1 CPUs   
> [ 0.070031] SMP: Total of 1 processors activated.   
> [ 0.074718] CPU: All CPU(s) started at EL2   
> [ 0.079281] kobject: 'devices' (ffffffc079823a98): kobject\_add\_internal: parent: '', set: ''   
> [ 0.088249] kobject: 'devices' (ffffffc079823a98): kobject\_uevent\_env   
> [ 0.094656] kobject: 'devices' (ffffffc079823a98): kobject\_uevent\_env: attempted to send uevent without kset!   
> [ 0.104531] kobject: 'dev' (ffffffc079823b00): kobject\_add\_internal: parent: '', set: ''   
> [ 0.113624] kobject: 'block' (ffffffc079823b80): kobject\_add\_internal: parent: 'dev', set: ''   
> [ 0.122656] kobject: 'char' (ffffffc079823c00): kobject\_add\_internal: parent: 'dev', set: ''   
> [ 0.131562] kobject: 'bus' (ffffffc079823c98): kobject\_add\_internal: parent: '', set: ''   
> [ 0.140687] kobject: 'bus' (ffffffc079823c98): kobject\_uevent\_env   
> [ 0.146749] kobject: 'bus' (ffffffc079823c98): kobject\_uevent\_env: attempted to send uevent without kset!   
> [ 0.156281] kobject: 'system' (ffffffc079823d18): kobject\_add\_internal: parent: 'devices', set: ''   
> [ 0.165718] kobject: 'system' (ffffffc079823d18): kobject\_uevent\_env   
> [ 0.172062] kobject: 'system' (ffffffc079823d18): kobject\_uevent\_env: attempted to send uevent without kset!   
> [ 0.181843] kobject: 'class' (ffffffc079823d98): kobject\_add\_internal: parent: '', set: ''   
> [ 0.191124] kobject: 'class' (ffffffc079823d98): kobject\_uevent\_env   
> [ 0.197343] kobject: 'class' (ffffffc079823d98): kobject\_uevent\_env: attempted to send uevent without kset!   
> [ 0.207062] kobject: 'firmware' (ffffffc079823e00): kobject\_add\_internal: parent: '', set: ''   
> [ 0.216593] device: 'platform': device\_add   
> [ 0.220656] kobject: 'platform' (ffffff80081d2680): kobject\_add\_internal: parent: 'devices', set: 'devices'   
> [ 0.230374] kobject: 'platform' (ffffff80081d2680): kobject\_uevent\_env   
> [ 0.236874] kobject: 'platform' (ffffff80081d2680): kobject\_uevent\_env: filter function caused the event to drop!   
> [ 0.247093] kobject: 'platform' (ffffffc079822818): kobject\_add\_internal: parent: 'bus', set: 'bus'   
> [ 0.256124] kobject: 'platform' (ffffffc079822818): kobject\_uevent\_env   
> [ 0.262624] kobject: 'platform' (ffffffc079822818): fill\_kobj\_path: path = '/bus/platform'   
> [ 0.270843] kobject: 'devices' (ffffffc079823e98): kobject\_add\_internal: parent: 'platform', set: ''   
> [ 0.280468] kobject: 'devices' (ffffffc079823e98): kobject\_uevent\_env   
> [ 0.286874] kobject: 'devices' (ffffffc079823e98): kobject\_uevent\_env: filter function caused the event to drop!   
> [ 0.297031] kobject: 'drivers' (ffffffc079823f18): kobject\_add\_internal: parent: 'platform', set: ''   
> [ 0.306656] kobject: 'drivers' (ffffffc079823f18): kobject\_uevent\_env   
> [ 0.313062] kobject: 'drivers' (ffffffc079823f18): kobject\_uevent\_env: filter function caused the event to drop!   
> [ 0.323187] bus: 'platform': registered   
> [ 0.326999] kobject: 'cpu' (ffffffc079822a18): kobject\_add\_internal: parent: 'bus', set: 'bus'   
> [ 0.335593] kobject: 'cpu' (ffffffc079822a18): kobject\_uevent\_env   
> [ 0.341656] kobject: 'cpu' (ffffffc079822a18): fill\_kobj\_path: path = '/bus/cpu'   
> [ 0.349031] kobject: 'devices' (ffffffc079823f98): kobject\_add\_internal: parent: 'cpu', set: ''   
> [ 0.358218] kobject: 'devices' (ffffffc079823f98): kobject\_uevent\_env   
> [ 0.364624] kobject: 'devices' (ffffffc079823f98): kobject\_uevent\_env: filter function caused the event to drop!   
> [ 0.374749] kobject: 'drivers' (ffffffc079820d18): kobject\_add\_internal: parent: 'cpu', set: ''   
> [ 0.383937] kobject: 'drivers' (ffffffc079820d18): kobject\_uevent\_env   
> [ 0.390374] kobject: 'drivers' (ffffffc079820d18): kobject\_uevent\_env: filter function caused the event to drop!   
> [ 0.400499] bus: 'cpu': registered   
> [ 0.403874] device: 'cpu': device\_add   
> [ 0.407531] kobject: 'cpu' (ffffffc079822c10): kobject\_add\_internal: parent: 'system', set: 'devices'   
> [ 0.416718] kobject: 'cpu' (ffffffc079822c10): kobject\_uevent\_env   
> [ 0.422781] kobject: 'cpu' (ffffffc079822c10): kobject\_uevent\_env: filter function caused the event to drop!   
> [ 0.432562] kobject: 'container' (ffffffc079822e18): kobject\_add\_internal: parent: 'bus', set: 'bus'   
> [ 0.441656] kobject: 'container' (ffffffc079822e18): kobject\_uevent\_env   
> [ 0.448249] kobject: 'container' (ffffffc079822e18): fill\_kobj\_path: path = '/bus/container'   
> [ 0.456656] kobject: 'devices' (ffffffc079820d98): kobject\_add\_internal: parent: 'container', set: ''   
> [ 0.466374] kobject: 'devices' (ffffffc079820d98): kobject\_uevent\_env   
> [ 0.472781] kobject: 'devices' (ffffffc079820d98): kobject\_uevent\_env: filter function caused the event to drop!   
> [ 0.482937] kobject: 'drivers' (ffffffc079820e18): kobject\_add\_internal: parent: 'container', set: ''   
> [ 0.492624] kobject: 'drivers' (ffffffc079820e18): kobject\_uevent\_env   
> [ 0.499031] kobject: 'drivers' (ffffffc079820e18): kobject\_uevent\_env: filter function caused the event to drop!   
> [ 0.509187] bus: 'container': registered   
> [ 0.513093] device: 'container': device\_add   
> [ 0.517249] kobject: 'container' (ffffffc079824010): kobject\_add\_internal: parent: 'system', set: 'devices'   
> [ 0.526937] kobject: 'container' (ffffffc079824010): kobject\_uevent\_env   
> [ 0.533531] kobject: 'container' (ffffffc079824010): kobject\_uevent\_env: filter function caused the event to drop!   
> [ 0.543843] kobject: 'devicetree' (ffffffc079820f98): kobject\_add\_internal: parent: 'firmware', set: ''   
> [ 0.553718] kobject: 'devicetree' (ffffffc079820f98): kobject\_uevent\_env   
> [ 0.560406] kobject: 'devicetree' (ffffffc079820f98): kobject\_uevent\_env: attempted to send uevent without kset!   
> [ 0.570531] doing early, parsing ARGS: 'earlycon=owl\_serial loglevel=8'   
> [ 0.577124] doing early: earlycon='owl\_serial'   
> [ 0.581562] doing early: loglevel='8'   
> [ 0.585187] doing core, parsing ARGS: 'earlycon=owl\_serial loglevel=8'   
> [ 0.591687] doing core: earlycon='owl\_serial'   
> [ 0.596031] doing core: loglevel='8'   
> [ 0.599593] kobject: 'kernel' (ffffffc079825000): kobject\_add\_internal: parent: '', set: ''   
> [ 0.608937] clocksource: jiffies: mask: 0xffffffff max\_cycles: 0xffffffff, max\_idle\_ns: 7645041785100000 ns   
> [ 0.618656] doing postcore, parsing ARGS: 'earlycon=owl\_serial loglevel=8'   
> [ 0.625499] doing postcore: earlycon='owl\_serial'   
> [ 0.630156] doing postcore: loglevel='8'   
> [ 0.634062] device class 'bdi': registering   
> [ 0.638218] kobject: 'bdi' (ffffffc079824218): kobject\_add\_internal: parent: 'class', set: 'class'   
> [ 0.647156] kobject: 'bdi' (ffffffc079824218): kobject\_uevent\_env   
> [ 0.653218] kobject: 'bdi' (ffffffc079824218): fill\_kobj\_path: path = '/class/bdi'   
> [ 0.660781] kobject: 'mm' (ffffffc079825100): kobject\_add\_internal: parent: 'kernel', set: ''   
> [ 0.669781] kobject: 'amba' (ffffffc079824418): kobject\_add\_internal: parent: 'bus', set: 'bus'   
> [ 0.678437] kobject: 'amba' (ffffffc079824418): kobject\_uevent\_env   
> [ 0.684593] kobject: 'amba' (ffffffc079824418): fill\_kobj\_path: path = '/bus/amba'   
> [ 0.692124] kobject: 'devices' (ffffffc079825198): kobject\_add\_internal: parent: 'amba', set: ''   
> [ 0.701406] kobject: 'devices' (ffffffc079825198): kobject\_uevent\_env   
> [ 0.707812] kobject: 'devices' (ffffffc079825198): kobject\_uevent\_env: filter function caused the event to drop!   
> [ 0.717968] kobject: 'drivers' (ffffffc079825218): kobject\_add\_internal: parent: 'amba', set: ''   
> [ 0.727249] kobject: 'drivers' (ffffffc079825218): kobject\_uevent\_env   
> [ 0.733656] kobject: 'drivers' (ffffffc079825218): kobject\_uevent\_env: filter function caused the event to drop!   
> [ 0.743781] bus: 'amba': registered   
> [ 0.747249] device class 'tty': registering   
> [ 0.751406] kobject: 'tty' (ffffffc079824618): kobject\_add\_internal: parent: 'class', set: 'class'   
> [ 0.760343] kobject: 'tty' (ffffffc079824618): kobject\_uevent\_env   
> [ 0.766406] kobject: 'tty' (ffffffc079824618): fill\_kobj\_path: path = '/class/tty'   
> [ 0.773937] doing arch, parsing ARGS: 'earlycon=owl\_serial loglevel=8'   
> [ 0.780437] doing arch: earlycon='owl\_serial'   
> [ 0.784781] doing arch: loglevel='8'   
> [ 0.788343] vdso: 2 pages (1 code @ ffffff8008186000, 1 data @ ffffff80081c8000)   
> [ 0.795874] DMA: preallocated 256 KiB pool for atomic allocations   
> [ 0.801781] of\_platform\_bus\_create() - skipping /memory, no compatible prop   
> [ 0.808687] of\_platform\_bus\_create() - skipping /chosen, no compatible prop   
> [ 0.815656] OF: \*\* translation for device /interrupt-controller@e00f1000 \*\*   
> [ 0.822562] OF: bus is default (na=2, ns=2) on /   
> [ 0.827156] OF: translating address: 00000000 e00f1000   
> [ 0.832281] OF: reached root node   
> [ 0.835562] OF: \*\* translation for device /interrupt-controller@e00f1000 \*\*   
> [ 0.842499] OF: bus is default (na=2, ns=2) on /   
> [ 0.847093] OF: translating address: 00000000 e00f2000   
> [ 0.852218] OF: reached root node   
> [ 0.855499] of\_irq\_parse\_one: dev=/interrupt-controller@e00f1000, index=0   
> [ 0.862249] OF: \*\* translation for device /interrupt-controller@e00f1000 \*\*   
> [ 0.869187] OF: bus is default (na=2, ns=2) on /   
> [ 0.873781] OF: translating address: 00000000 e00f1000   
> [ 0.878906] OF: reached root node   
> [ 0.882187] OF: \*\* translation for device /interrupt-controller@e00f1000 \*\*   
> [ 0.889124] OF: bus is default (na=2, ns=2) on /   
> [ 0.893718] OF: translating address: 00000000 e00f2000   
> [ 0.898843] OF: reached root node   
> [ 0.902124] OF: \*\* translation for device /interrupt-controller@e00f1000 \*\*   
> [ 0.909062] OF: bus is default (na=2, ns=2) on /   
> [ 0.913656] OF: translating address: 00000000 e00f1000   
> [ 0.918781] OF: reached root node   
> [ 0.922062] of\_dma\_get\_range: no dma-ranges found for node(/interrupt-controller@e00f1000)   
> [ 0.930312] platform e00f1000.interrupt-controller: device is not dma coherent   
> [ 0.937499] platform e00f1000.interrupt-controller: device is not behind an iommu   
> [ 0.944937] device: 'e00f1000.interrupt-controller': device\_add   
> [ 0.950843] kobject: 'e00f1000.interrupt-controller' (ffffffc079824820): kobject\_add\_internal: parent: 'platform', set: 'devices'   
> [ 0.962437] bus: 'platform': add device e00f1000.interrupt-controller   
> [ 0.968874] kobject: 'e00f1000.interrupt-controller' (ffffffc079824820): kobject\_uevent\_env   
> [ 0.977187] kobject: 'e00f1000.interrupt-controller' (ffffffc079824820): fill\_kobj\_path: path = '/devices/platform/e00f1000.interrupt-controller'   
> [ 0.990218] of\_irq\_parse\_one: dev=/timer, index=0   
> [ 0.994874] intspec=1 intlen=12   
> [ 0.998062] intsize=3 intlen=12   
> [ 1.001281] of\_irq\_parse\_raw: /interrupt-controller@e00f1000:00000001,0000000d,00000f08   
> [ 1.009343] of\_irq\_parse\_raw: ipar=/interrupt-controller@e00f1000, size=3   
> [ 1.016093] -> addrsize=0   
> [ 1.018781] -> got it !   
> [ 1.021281] of\_irq\_parse\_one: dev=/timer, index=1   
> [ 1.025968] intspec=1 intlen=12   
> [ 1.029187] intsize=3 intlen=12   
> [ 1.032374] of\_irq\_parse\_raw: /interrupt-controller@e00f1000:00000001,0000000e,00000f08   
> [ 1.040437] of\_irq\_parse\_raw: ipar=/interrupt-controller@e00f1000, size=3   
> [ 1.047218] -> addrsize=0   
> [ 1.049906] -> got it !   
> [ 1.052406] of\_irq\_parse\_one: dev=/timer, index=2   
> [ 1.057093] intspec=1 intlen=12   
> [ 1.060281] intsize=3 intlen=12   
> [ 1.063499] of\_irq\_parse\_raw: /interrupt-controller@e00f1000:00000001,0000000b,00000f08   
> [ 1.071562] of\_irq\_parse\_raw: ipar=/interrupt-controller@e00f1000, size=3   
> [ 1.078312] -> addrsize=0   
> [ 1.080999] -> got it !   
> [ 1.083531] of\_irq\_parse\_one: dev=/timer, index=3   
> [ 1.088187] intspec=1 intlen=12   
> [ 1.091406] intsize=3 intlen=12   
> [ 1.094624] of\_irq\_parse\_raw: /interrupt-controller@e00f1000:00000001,0000000a,00000f08   
> [ 1.102687] of\_irq\_parse\_raw: ipar=/interrupt-controller@e00f1000, size=3   
> [ 1.109437] -> addrsize=0   
> [ 1.112124] -> got it !   
> [ 1.114624] of\_irq\_parse\_one: dev=/timer, index=4   
> [ 1.119312] intspec=1 intlen=12   
> [ 1.122531] intsize=3 intlen=12   
> [ 1.125718] of\_irq\_parse\_one: dev=/timer, index=0   
> [ 1.130406] intspec=1 intlen=12   
> [ 1.133624] intsize=3 intlen=12   
> [ 1.136812] of\_irq\_parse\_raw: /interrupt-controller@e00f1000:00000001,0000000d,00000f08   
> [ 1.144874] of\_irq\_parse\_raw: ipar=/interrupt-controller@e00f1000, size=3   
> [ 1.151624] -> addrsize=0   
> [ 1.154312] -> got it !   
> [ 1.156843] of\_irq\_parse\_one: dev=/timer, index=1   
> [ 1.161531] intspec=1 intlen=12   
> [ 1.164718] intsize=3 intlen=12   
> [ 1.167937] of\_irq\_parse\_raw: /interrupt-controller@e00f1000:00000001,0000000e,00000f08   
> [ 1.175999] of\_irq\_parse\_raw: ipar=/interrupt-controller@e00f1000, size=3   
> [ 1.182749] -> addrsize=0   
> [ 1.185437] -> got it !   
> [ 1.187968] of\_irq\_parse\_one: dev=/timer, index=2   
> [ 1.192624] intspec=1 intlen=12   
> [ 1.195843] intsize=3 intlen=12   
> [ 1.199031] of\_irq\_parse\_raw: /interrupt-controller@e00f1000:00000001,0000000b,00000f08   
> [ 1.207093] of\_irq\_parse\_raw: ipar=/interrupt-controller@e00f1000, size=3   
> [ 1.213874] -> addrsize=0   
> [ 1.216562] -> got it !   
> [ 1.219062] of\_irq\_parse\_one: dev=/timer, index=3   
> [ 1.223749] intspec=1 intlen=12   
> [ 1.226968] intsize=3 intlen=12   
> [ 1.230156] of\_irq\_parse\_raw: /interrupt-controller@e00f1000:00000001,0000000a,00000f08   
> [ 1.238218] of\_irq\_parse\_raw: ipar=/interrupt-controller@e00f1000, size=3   
> [ 1.244968] -> addrsize=0   
> [ 1.247656] -> got it !   
> [ 1.250187] of\_dma\_get\_range: no dma-ranges found for node(/timer)   
> [ 1.256343] platform timer: device is not dma coherent   
> [ 1.261437] platform timer: device is not behind an iommu   
> [ 1.266812] device: 'timer': device\_add   
> [ 1.270624] kobject: 'timer' (ffffffc079824a20): kobject\_add\_internal: parent: 'platform', set: 'devices'   
> [ 1.280156] bus: 'platform': add device timer   
> [ 1.284499] kobject: 'timer' (ffffffc079824a20): kobject\_uevent\_env   
> [ 1.290749] kobject: 'timer' (ffffffc079824a20): fill\_kobj\_path: path = '/devices/platform/timer'   
> [ 1.299593] doing subsys, parsing ARGS: 'earlycon=owl\_serial loglevel=8'   
> [ 1.306249] doing subsys: earlycon='owl\_serial'   
> [ 1.310749] doing subsys: loglevel='8'   
> [ 1.314499] device: 'cpu0': device\_add   
> [ 1.318218] kobject: 'cpu0' (ffffffc07ffe1468): kobject\_add\_internal: parent: 'cpu', set: 'devices'   
> [ 1.327218] bus: 'cpu': add device cpu0   
> [ 1.331031] kobject: 'cpu0' (ffffffc07ffe1468): kobject\_uevent\_env   
> [ 1.337187] kobject: 'cpu0' (ffffffc07ffe1468): fill\_kobj\_path: path = '/devices/system/cpu/cpu0'   
> [ 1.346156] device class 'misc': registering   
> [ 1.350281] kobject: 'misc' (ffffffc079824e18): kobject\_add\_internal: parent: 'class', set: 'class'   
> [ 1.359281] kobject: 'misc' (ffffffc079824e18): kobject\_uevent\_env   
> [ 1.365437] kobject: 'misc' (ffffffc079824e18): fill\_kobj\_path: path = '/class/misc'   
> [ 1.373156] device class 'power\_supply': registering   
> [ 1.378093] kobject: 'power\_supply' (ffffffc079803018): kobject\_add\_internal: parent: 'class', set: 'class'   
> [ 1.387812] kobject: 'power\_supply' (ffffffc079803018): kobject\_uevent\_env   
> [ 1.394656] kobject: 'power\_supply' (ffffffc079803018): fill\_kobj\_path: path = '/class/power\_supply'   
> [ 1.403749] doing fs, parsing ARGS: 'earlycon=owl\_serial loglevel=8'   
> [ 1.410093] doing fs: earlycon='owl\_serial'   
> [ 1.414249] doing fs: loglevel='8'   
> [ 1.417656] clocksource: Switched to clocksource arch\_sys\_counter   
> [ 1.423718] device class 'mem': registering   
> [ 1.427843] kobject: 'mem' (ffffffc079827018): kobject\_add\_internal: parent: 'class', set: 'class'   
> [ 1.436781] kobject: 'mem' (ffffffc079827018): kobject\_uevent\_env   
> [ 1.442843] kobject: 'mem' (ffffffc079827018): fill\_kobj\_path: path = '/class/mem'   
> [ 1.450374] device: 'null': device\_add   
> [ 1.454124] kobject: 'virtual' (ffffffc079826080): kobject\_add\_internal: parent: 'devices', set: ''   
> [ 1.463656] kobject: 'mem' (ffffffc079826100): kobject\_add\_internal: parent: 'virtual', set: '(null)'   
> [ 1.472843] kobject: 'null' (ffffffc079827210): kobject\_add\_internal: parent: 'mem', set: 'devices'   
> [ 1.481843] kobject: 'null' (ffffffc079827210): kobject\_uevent\_env   
> [ 1.487999] kobject: 'null' (ffffffc079827210): fill\_kobj\_path: path = '/devices/virtual/mem/null'   
> [ 1.496937] device: 'zero': device\_add   
> [ 1.500656] kobject: 'zero' (ffffffc079827410): kobject\_add\_internal: parent: 'mem', set: 'devices'   
> [ 1.509656] kobject: 'zero' (ffffffc079827410): kobject\_uevent\_env   
> [ 1.515812] kobject: 'zero' (ffffffc079827410): fill\_kobj\_path: path = '/devices/virtual/mem/zero'   
> [ 1.524749] device: 'full': device\_add   
> [ 1.528468] kobject: 'full' (ffffffc079827610): kobject\_add\_internal: parent: 'mem', set: 'devices'   
> [ 1.537468] kobject: 'full' (ffffffc079827610): kobject\_uevent\_env   
> [ 1.543624] kobject: 'full' (ffffffc079827610): fill\_kobj\_path: path = '/devices/virtual/mem/full'   
> [ 1.552562] device: 'random': device\_add   
> [ 1.556468] kobject: 'random' (ffffffc079827810): kobject\_add\_internal: parent: 'mem', set: 'devices'   
> [ 1.565656] kobject: 'random' (ffffffc079827810): kobject\_uevent\_env   
> [ 1.571968] kobject: 'random' (ffffffc079827810): fill\_kobj\_path: path = '/devices/virtual/mem/random'   
> [ 1.581249] device: 'urandom': device\_add   
> [ 1.585249] kobject: 'urandom' (ffffffc079827a10): kobject\_add\_internal: parent: 'mem', set: 'devices'   
> [ 1.594499] kobject: 'urandom' (ffffffc079827a10): kobject\_uevent\_env   
> [ 1.600937] kobject: 'urandom' (ffffffc079827a10): fill\_kobj\_path: path = '/devices/virtual/mem/urandom'   
> [ 1.610374] device: 'kmsg': device\_add   
> [ 1.614093] kobject: 'kmsg' (ffffffc079827c10): kobject\_add\_internal: parent: 'mem', set: 'devices'   
> [ 1.623124] kobject: 'kmsg' (ffffffc079827c10): kobject\_uevent\_env   
> [ 1.629249] kobject: 'kmsg' (ffffffc079827c10): fill\_kobj\_path: path = '/devices/virtual/mem/kmsg'   
> [ 1.638187] device: 'tty': device\_add   
> [ 1.641843] kobject: 'tty' (ffffffc079826280): kobject\_add\_internal: parent: 'virtual', set: '(null)'   
> [ 1.651031] kobject: 'tty' (ffffffc079827e10): kobject\_add\_internal: parent: 'tty', set: 'devices'   
> [ 1.659937] kobject: 'tty' (ffffffc079827e10): kobject\_uevent\_env   
> [ 1.665999] kobject: 'tty' (ffffffc079827e10): fill\_kobj\_path: path = '/devices/virtual/tty/tty'   
> [ 1.674781] device: 'console': device\_add   
> [ 1.678749] kobject: 'console' (ffffffc079829010): kobject\_add\_internal: parent: 'tty', set: 'devices'   
> [ 1.688031] kobject: 'console' (ffffffc079829010): kobject\_uevent\_env   
> [ 1.694437] kobject: 'console' (ffffffc079829010): fill\_kobj\_path: path = '/devices/virtual/tty/console'   
> [ 1.703937] doing device, parsing ARGS: 'earlycon=owl\_serial loglevel=8'   
> [ 1.710562] doing device: earlycon='owl\_serial'   
> [ 1.715062] doing device: loglevel='8'   
> [ 1.718812] bus: 'platform': add driver alarmtimer   
> [ 1.723562] kobject: 'alarmtimer' (ffffffc079828600): kobject\_add\_internal: parent: 'drivers', set: 'drivers'   
> [ 1.733437] kobject: 'alarmtimer' (ffffffc079828600): kobject\_uevent\_env   
> [ 1.740124] kobject: 'alarmtimer' (ffffffc079828600): fill\_kobj\_path: path = '/bus/platform/drivers/alarmtimer'   
> [ 1.750156] Registering platform device 'alarmtimer'. Parent at platform   
> [ 1.756843] device: 'alarmtimer': device\_add   
> [ 1.761093] kobject: 'alarmtimer' (ffffffc079829220): kobject\_add\_internal: parent: 'platform', set: 'devices'   
> [ 1.771062] bus: 'platform': add device alarmtimer   
> [ 1.775812] kobject: 'alarmtimer' (ffffffc079829220): kobject\_uevent\_env   
> [ 1.782499] kobject: 'alarmtimer' (ffffffc079829220): fill\_kobj\_path: path = '/devices/platform/alarmtimer'   
> [ 1.792218] bus: 'platform': driver\_probe\_device: matched device alarmtimer with driver alarmtimer   
> [ 1.801124] bus: 'platform': really\_probe: probing driver alarmtimer with device alarmtimer   
> [ 1.809437] devices\_kset: Moving alarmtimer to end of list   
> [ 1.814906] driver: 'alarmtimer': driver\_bound: bound to device 'alarmtimer'   
> [ 1.821937] bus: 'platform': really\_probe: bound device alarmtimer to driver alarmtimer   
> [ 1.829999] workingset: timestamp\_bits=60 max\_order=19 bucket\_order=0   
> [ 1.836312] Failed to find cpu0 device node   
> [ 1.840468] Unable to detect cache hierarchy from DT for CPU 0   
> [ 1.846281] bus: 'platform': add driver gpio-clk   
> [ 1.850874] kobject: 'gpio-clk' (ffffffc079828900): kobject\_add\_internal: parent: 'drivers', set: 'drivers'   
> [ 1.860593] kobject: 'gpio-clk' (ffffffc079828900): kobject\_uevent\_env   
> [ 1.867093] kobject: 'gpio-clk' (ffffffc079828900): fill\_kobj\_path: path = '/bus/platform/drivers/gpio-clk'   
> [ 1.876781] doing late, parsing ARGS: 'earlycon=owl\_serial loglevel=8'   
> [ 1.883281] doing late: earlycon='owl\_serial'   
> [ 1.887624] doing late: loglevel='8'   
> [ 1.891187] device: 'cpu\_dma\_latency': device\_add   
> [ 1.895843] kobject: 'misc' (ffffffc079826780): kobject\_add\_internal: parent: 'virtual', set: '(null)'   
> [ 1.905124] kobject: 'cpu\_dma\_latency' (ffffffc079829610): kobject\_add\_internal: parent: 'misc', set: 'devices'   
> [ 1.915187] kobject: 'cpu\_dma\_latency' (ffffffc079829610): kobject\_uevent\_env   
> [ 1.922281] kobject: 'cpu\_dma\_latency' (ffffffc079829610): fill\_kobj\_path: path = '/devices/virtual/misc/cpu\_dma\_latency'   
> [ 1.933218] device: 'network\_latency': device\_add   
> [ 1.937874] kobject: 'network\_latency' (ffffffc079829810): kobject\_add\_internal: parent: 'misc', set: 'devices'   
> [ 1.947937] kobject: 'network\_latency' (ffffffc079829810): kobject\_uevent\_env   
> [ 1.955031] kobject: 'network\_latency' (ffffffc079829810): fill\_kobj\_path: path = '/devices/virtual/misc/network\_latency'   
> [ 1.965968] device: 'network\_throughput': device\_add   
> [ 1.970906] kobject: 'network\_throughput' (ffffffc079829a10): kobject\_add\_internal: parent: 'misc', set: 'devices'   
> [ 1.981218] kobject: 'network\_throughput' (ffffffc079829a10): kobject\_uevent\_env   
> [ 1.988593] kobject: 'network\_throughput' (ffffffc079829a10): fill\_kobj\_path: path = '/devices/virtual/misc/network\_throughput'   
> [ 2.000031] device: 'memory\_bandwidth': device\_add   
> [ 2.004781] kobject: 'memory\_bandwidth' (ffffffc079829c10): kobject\_add\_internal: parent: 'misc', set: 'devices'   
> [ 2.014937] kobject: 'memory\_bandwidth' (ffffffc079829c10): kobject\_uevent\_env   
> [ 2.022124] kobject: 'memory\_bandwidth' (ffffffc079829c10): fill\_kobj\_path: path = '/devices/virtual/misc/memory\_bandwidth'   
> [ 2.033437] Warning: unable to open an initial console.   
> [ 2.038531] Freeing unused kernel memory: 120K (ffffff80081a3000 - ffffff80081c1000)   
> [ 2.046124] This architecture does not have kernel memory protection.   
> [ 2.052593] Kernel panic - not syncing: No working init found. Try passing init= option to kernel. See Linux Documentation/init.txt for guidance.   
> [ 2.065624] Kernel Offset: disabled   
> [ 2.069093] Memory Limit: none   
> [ 2.072124] ---[ end Kernel panic - not syncing: No working init found. Try passing init= option to kernel. See Linux Documentation/init.txt for guidance.

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/linux_application/kernel_debug_enable.html)。*

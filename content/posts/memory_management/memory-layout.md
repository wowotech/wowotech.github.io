---
title: "内存初始化代码分析（二）：内存布局"
date: 2016-11-18T18:25:20+08:00
url: "/memory_management/memory-layout.html"
gid: "355"
emlog_type: "blog"
summary: "同样的，本文是 内存初始化 文章的一份补充文档，希望能够通过这样的一份文档，细致的展示在初始化阶段，Linux 4.4.6内核如何从device tree中提取信息，完成内存布局的任务。具体的cpu体系结构选择的是ARM64。"
author: "linuxer"
category: "内存管理"
category_alias: "memory_management"
tags: ["Memory", "内存布局", "layout"]
views: 35062
comment_count: 12
aliases:
  - "/memory_management/355.html"
  - "/355.html"
---

一、前言

同样的，本文是[内存初始化](/memory_management/mm-init-1.html)文章的一份补充文档，希望能够通过这样的一份文档，细致的展示在初始化阶段，Linux 4.4.6内核如何从device tree中提取信息，完成内存布局的任务。具体的cpu体系结构选择的是ARM64。

二、memory type region的构建

memory type是一个memblock模块（内核初始化阶段的内存管理模块）的术语，memblock将内存块分成两种类型：一种是memory type，另外一种是reserved type，分别用数组来管理系统中的两种类型的memory region。本小节描述的是系统如何在初始化阶段构建memory type的数组。

1、扫描device tree

在完成fdt内存区域的地址映射之后（fixmap\_remap\_fdt），内核会对fdt进行扫描，以便完成memory type数组的构建。具体代码位于setup\_machine\_fdt--->early\_init\_dt\_scan--->early\_init\_dt\_scan\_nodes中：

> void \_\_init early\_init\_dt\_scan\_nodes(void)   
> {   
> of\_scan\_flat\_dt(early\_init\_dt\_scan\_chosen, boot\_command\_line); －－－－－－（1）   
> of\_scan\_flat\_dt(early\_init\_dt\_scan\_root, NULL);   
> of\_scan\_flat\_dt(early\_init\_dt\_scan\_memory, NULL);－－－－－－－－－－－－－（2）   
> }

（1）of\_scan\_flat\_dt函数是用来scan整个device tree，针对每一个node调用callback函数，因此，这里实际上是针对设备树中的每一个节点调用early\_init\_dt\_scan\_chosen函数。之所以这么做是因为device tree blob刚刚完成地址映射，还没有展开，我们只能使用这种比较笨的办法。这句代码主要是寻址chosen node，并解析，将相关数据放入到boot\_command\_line。

（2）概念同上，不过是针对memory node进行scan。

2、传统的命令行参数解析

> int \_\_init early\_init\_dt\_scan\_chosen(unsigned long node, const char \*uname, int depth, void \*data)   
> {   
> int l;   
> const char \*p;
>
> if (depth != 1 || !data ||   
> (strcmp(uname, "chosen") != 0 && strcmp(uname, "chosen@0") != 0))   
> return 0; －－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－（1）
>
> early\_init\_dt\_check\_for\_initrd(node); －－－－－－－－－－－－－－－－－－－－（2）
>
> /\* Retrieve command line \*/   
> p = of\_get\_flat\_dt\_prop(node, "bootargs", &l);   
> if (p != NULL && l > 0)   
> strlcpy(data, p, min((int)l, COMMAND\_LINE\_SIZE)); －－－－－－－－－－－－（3）
>
> #ifdef CONFIG\_CMDLINE   
> #ifndef CONFIG\_CMDLINE\_FORCE   
> if (!((char \*)data)[0])   
> #endif   
> strlcpy(data, CONFIG\_CMDLINE, COMMAND\_LINE\_SIZE);   
> #endif /\* CONFIG\_CMDLINE \*/ －－－－－－－－－－－－－－－－－－－－－－－（4）
>
> return 1;   
> }

（1）上面我们说过，early\_init\_dt\_scan\_chosen会为device tree中的每一个node而调用一次，因此，为了效率，不是chosen node的节点我们必须赶紧闪人。由于chosen node是root node的子节点，因此其depth必须是1。这里depth不是1的节点，节点名字不是"chosen"或者[chosen@0](mailto:chosen@0)和我们毫无关系，立刻返回。

（2）解析chosen node中的initrd的信息

（3）解析chosen node中的bootargs（命令行参数）并将其copy到boot\_command\_line。

（4）一般而言，内核有可能会定义一个default command line string（CONFIG\_CMDLINE），如果bootloader没有通过device tree传递命令行参数过来，那么可以考虑使用default参数。如果系统定义了CONFIG\_CMDLINE\_FORCE，那么系统强制使用缺省命令行参数，bootloader传递过来的是无效的。

3、memory node解析

> int \_\_init early\_init\_dt\_scan\_memory(unsigned long node, const char \*uname, int depth, void \*data)   
> {   
> const char \*type = of\_get\_flat\_dt\_prop(node, "device\_type", NULL);   
> const \_\_be32 \*reg, \*endp;   
> int l;   
> if (type == NULL) {   
> if (!IS\_ENABLED(CONFIG\_PPC32) || depth != 1 || strcmp(uname, "memory@0") != 0)   
> return 0;   
> } else if (strcmp(type, "memory") != 0)   
> return 0; －－－－－－－－－－－－－－－－－－－－－－－－－－－－－（1）
>
> reg = of\_get\_flat\_dt\_prop(node, "linux,usable-memory", &l);   
> if (reg == NULL)   
> reg = of\_get\_flat\_dt\_prop(node, "reg", &l);－－－－－－－－－－－－－－－（2）   
> if (reg == NULL)   
> return 0;
>
> endp = reg + (l / sizeof(\_\_be32)); －－－－－－－－－－－－－－－－－－－－（3）
>
> while ((endp - reg) >= (dt\_root\_addr\_cells + dt\_root\_size\_cells)) {   
> u64 base, size;
>
> base = dt\_mem\_next\_cell(dt\_root\_addr\_cells, ®);   
> size = dt\_mem\_next\_cell(dt\_root\_size\_cells, ®); －－－－－－－－－－（4）
>
> early\_init\_dt\_add\_memory\_arch(base, size);－－－－－－－－－－－－－－（5）   
> }
>
> return 0;   
> }

（1）如果该memory node是root node的子节点的话，那么它一定是有device\_type属性并且其值是字符串”memory”。不是的话就可以返回了。不过node没有定义device\_type属性怎么办？大部分的平台都可以直接返回了，除了PPC32，对于这个平台，如果memory node是更深层次的节点的话，那么它是没有device\_type属性的，这时候可以根据node name来判断。当然，目标都是一致的，不是自己关注的node就赶紧闪人。

（2）该memory node的物理地址信息保存在"linux,usable-memory"或者"reg"属性中（reg是我们常用的）

（3）l / sizeof(\_\_be32)是reg属性值的cell数目，reg指向第一个cell，endp指向最后一个cell。

（4）memory node的reg属性值其实就是一个数组，数组中的每一个entry都是base address和size的二元组。解析reg属性需要两个参数，dt\_root\_addr\_cells和dt\_root\_size\_cells，这两个参数分别定义了root节点的子节点（比如说memory node）reg属性中base address和size的cell数目，如果等于1，基地址（或者size）用一个32-bit的cell表示。对于ARMv8，一般dt\_root\_addr\_cells和dt\_root\_size\_cells等于2，表示基地址（或者size）用两个32-bit的cell表示。

注：dt\_root\_addr\_cells和dt\_root\_size\_cells这两个参数的解析在early\_init\_dt\_scan\_root中完成。

（5）针对该memory mode中的每一个memory region，调用early\_init\_dt\_add\_memory\_arch向系统注册memory type的内存区域（实际上是通过memblock\_add完成的）。

4、解析memory相关的early option

setup\_arch--->parse\_early\_param函数中会对early options解析解析，这会导致下面代码的执行：

> static int \_\_init early\_mem(char \*p)   
> {
>
> memory\_limit = memparse(p, &p) & PAGE\_MASK;
>
> return 0;   
> }   
> early\_param("mem", early\_mem);

在过去，没有device tree的时代，mem这个命令行参数传递了memory bank的信息，内核根据这个信息来创建系统内存的初始布局。在ARM64中，由于强制使用device tree，因此mem这个启动参数失去了本来的意义，现在它只是定义了memory的上限（最大的系统内存地址），可以限制DTS传递过来的内存参数。

三、reserved type region的构建

保留内存的定义主要在fixmap\_remap\_fdt和arm64\_memblock\_init函数中进行，我们会按照代码顺序逐一进行各种各样reserved type的memory region的构建。

1、保留fdt占用的内存，代码如下：

> void \*\_\_init fixmap\_remap\_fdt(phys\_addr\_t dt\_phys)   
> {……
>
> memblock\_reserve(dt\_phys, size);
>
> ……}

fixmap\_remap\_fdt主要是为fdt建立地址映射，在该函数的最后，顺便就调用memblock\_reserve保留了该段内存。

2、保留内核和initrd占用的内容，代码如下：

> void \_\_init arm64\_memblock\_init(void)   
> {   
> memblock\_enforce\_memory\_limit(memory\_limit); －－－－－－－－－－－－－－－－（1）   
> memblock\_reserve(\_\_pa(\_text), \_end - \_text);－－－－－－－－－－－－－－－－－－（2）   
> #ifdef CONFIG\_BLK\_DEV\_INITRD   
> if (initrd\_start)   
> memblock\_reserve(\_\_virt\_to\_phys(initrd\_start), initrd\_end - initrd\_start);－－－－－－（3）   
> #endif   
> ……}

（1）我们前面解析了DTS的memory节点，已经向系统加入了不少的memory type的region，当然reserved memory block也会有一些，例如DTB对应的memory就是reserved。memory\_limit可以对这些DTS的设定给出上限，memblock\_enforce\_memory\_limit函数会根据这个上限，修改各个memory region的base和size，此外还将大于memory\_limit的memory block（包括memory type和reserved type）从列表中删掉。

（2）reserve内核代码、数据区等（\_text到\_end那一段，具体的内容可以参考内核链接脚本）

（3）保留initital ramdisk image区域（从initrd\_start到initrd\_end区域）

3、通过early\_init\_fdt\_scan\_reserved\_mem函数来分析dts中的节点，从而进行保留内存的动作，代码如下：

> void \_\_init early\_init\_fdt\_scan\_reserved\_mem(void)   
> {   
> int n;   
> u64 base, size;
>
> if (!initial\_boot\_params)－－－－－－－－－－－－－－－－－－－－－－－－（1）   
> return;
>
> /\* Process header /memreserve/ fields \*/   
> for (n = 0; ; n++) {   
> fdt\_get\_mem\_rsv(initial\_boot\_params, n, &base, &size);－－－－－－－－（2）   
> if (!size)   
> break;   
> early\_init\_dt\_reserve\_memory\_arch(base, size, 0);－－－－－－－－－－－（3）   
> }
>
> of\_scan\_flat\_dt(\_\_fdt\_scan\_reserved\_mem, NULL);－－－－－－－－－－－－（4）   
> fdt\_init\_reserved\_mem();   
> }

（1）initial\_boot\_params实际上就是fdt对应的虚拟地址。在early\_init\_dt\_verify中设定的。如果系统中都没有有效的fdt，那么没有什么可以scan的，return，走人。

（2）分析fdt中的 /memreserve/ fields ，进行内存的保留。在fdt的header中定义了一组memory reserve参数，其具体的位置是fdt base address + off\_mem\_rsvmap。off\_mem\_rsvmap是fdt header中的一个成员，如下：

> struct fdt\_header {   
> ……   
> fdt32\_t off\_mem\_rsvmap;－－－－－－/memreserve/ fields offset   
> ……};

fdt header中的memreserve可以定义多个，每个都是（address，size）二元组，最后以0，0结束。

（3）保留每一个/memreserve/ fields定义的memory region，底层是通过memblock\_reserve接口函数实现的。

（4）对fdt中的每一个节点调用\_\_fdt\_scan\_reserved\_mem函数，进行reserved-memory节点的扫描，之后调用fdt\_init\_reserved\_mem函数进行内存预留的动作，具体参考下一小节描述。

4、解析reserved-memory节点的内存，代码如下：

> static int \_\_init \_\_fdt\_scan\_reserved\_mem(unsigned long node, const char \*uname,   
> int depth, void \*data)   
> {   
> static int found;   
> const char \*status;   
> int err;
>
> if (!found && depth == 1 && strcmp(uname, "reserved-memory") == 0) { －－－－－－－（1）   
> if (\_\_reserved\_mem\_check\_root(node) != 0) {   
> pr\_err("Reserved memory: unsupported node format, ignoring\n");   
> return 1;   
> }   
> found = 1; －－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－（2）   
> return 0;   
> } else if (!found) {   
> return 0; －－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－（3）   
> } else if (found && depth < 2) { －－－－－－－－－－－－－－－－－－－－－－－－－（4）   
> return 1;   
> }
>
> status = of\_get\_flat\_dt\_prop(node, "status", NULL); －－－－－－－－－－－－－－－－（5）   
> if (status && strcmp(status, "okay") != 0 && strcmp(status, "ok") != 0)   
> return 0;
>
> err = \_\_reserved\_mem\_reserve\_reg(node, uname); －－－－－－－－－－－－－－－－（6）   
> if (err == -ENOENT && of\_get\_flat\_dt\_prop(node, "size", NULL))   
> fdt\_reserved\_mem\_save\_node(node, uname, 0, 0); －－－－－－－－－－－－－－－（7）
>
> /\* scan next node \*/   
> return 0;   
> }

（1）found 变量记录了是否搜索到一个reserved-memory节点，如果没有，我们的首要目标是找到一个reserved-memory节点。reserved-memory节点的特点包括：是root node的子节点（depth == 1），node name是"reserved-memory"，这可以过滤掉一大票无关节点，从而加快搜索速度。

（2）reserved-memory节点应该包括#address-cells、#size-cells和range属性，并且#address-cells和#size-cells的属性值应该等于根节点对应的属性值，如果检查通过（\_\_reserved\_mem\_check\_root），那么说明找到了一个正确的reserved-memory节点，可以去往下一个节点了。当然，下一个节点往往是reserved-memory节点的subnode，也就是真正的定义各段保留内存的节点。更详细的关于reserved-memory的设备树定义可以参考Documentation\devicetree\bindings\reserved-memory\reserved-memory.txt文件。

（3）没有找到reserved-memory节点之前，of\_scan\_flat\_dt会不断的遍历下一个节点，而在\_\_fdt\_scan\_reserved\_mem函数中返回0表示让搜索继续，如果返回1，表示搜索停止。

（4）如果找到了一个reserved-memory节点，并且完成了对其所有subnode的scan，那么是退出整个reserved memory的scan过程了。

（5）如果定义了status属性，那么要求其值必须要是ok或者okay，当然，你也可以不定义该属性（这是一般的做法）。

（6）定义reserved memory有两种方法，一种是静态定义，也就是定义了reg属性，这时候，可以通过调用\_\_reserved\_mem\_reserve\_reg函数解析reg的（address，size）的二元数组，逐一对每一个定义的memory region进行预留。实际的预留内存动作可以调用memblock\_reserve或者memblock\_remove，具体调用哪一个是和该节点是否定义no-map属性相关，如果定义了no-map属性，那么说明这段内存操作系统根本不需要进行地址映射，也就是说这块内存是不归操作系统内存管理模块来管理的，而是归于具体的驱动使用（在device tree中，设备节点可以定义memory-region节点来引用在memory node中定义的保留内存，具体可以参考reserved-memory.txt文件）。

（7）另外一种定义reserved memory的方法是动态定义，也就是说定义了该内存区域的size（也可以定义alignment或者alloc-range进一步约定动态分配的reserved memory属性，不过这些属性都是option的），但是不指定具体的基地址，让操作系统自己来分配这段memory。

5、预留reserved-memory节点的内存

device tree中的reserved-memory节点及其子节点静态或者动态定义了若干的reserved memory region，静态定义的memory region起始地址和size都是确定的，因此可以立刻调用memblock的模块进行内存区域的预留，但是对于动态定义的memory region，\_\_fdt\_scan\_reserved\_mem只是将信息保存在了reserved\_mem全局变量中，并没有进行实际的内存预留动作，具体的操作在fdt\_init\_reserved\_mem函数中，代码如下：

> void \_\_init fdt\_init\_reserved\_mem(void)   
> {   
> int i;
>
> \_\_rmem\_check\_for\_overlap(); －－－－－－－－－－－－－－－－－－－－－－－－－（1）
>
> for (i = 0; i < reserved\_mem\_count; i++) {－－遍历每一个reserved memory region   
> struct reserved\_mem \*rmem = &reserved\_mem[i];   
> unsigned long node = rmem->fdt\_node;   
> int len;   
> const \_\_be32 \*prop;   
> int err = 0;
>
> prop = of\_get\_flat\_dt\_prop(node, "phandle", &len);－－－－－－－－－－－－－－－（2）   
> if (!prop)   
> prop = of\_get\_flat\_dt\_prop(node, "linux,phandle", &len);   
> if (prop)   
> rmem->phandle = of\_read\_number(prop, len/4);
>
> if (rmem->size == 0)－－－－－－－－－－－－－－－－－－－－－－－－－－－－（3）   
> err = \_\_reserved\_mem\_alloc\_size(node, rmem->name,   
> &rmem->base, &rmem->size);   
> if (err == 0)   
> \_\_reserved\_mem\_init\_node(rmem);－－－－－－－－－－－－－－－－－－－－（4）   
> }   
> }

（1）检查静态定义的 reserved memory region之间是否有重叠区域，如果有重叠，这里并不会对reserved memory region的base和size进行调整，只是打印出错信息而已。

（2）每一个需要被其他node引用的node都需要定义"phandle", 或者"linux,phandle"。虽然在实际的device tree source中看不到这个属性，实际上dtc会完美的处理这一切的。

（3）size等于0的memory region表示这是一个动态分配region，base address尚未定义，因此我们需要通过\_\_reserved\_mem\_alloc\_size函数对节点进行分析（size、alignment等属性），然后调用memblock的alloc接口函数进行memory block的分配，最终的结果是确定base address和size，并将这段memory region从memory type的数组中移到reserved type的数组中。当然，如果定义了no-map属性，那么这段memory会从系统中之间删除（memory type和reserved type数组中都没有这段memory的定义）。

（4）保留内存有两种使用场景，一种是被特定的驱动使用，这时候在特定驱动的初始化函数（probe函数）中自然会进行处理。还有一种场景就是被所有驱动或者内核模块使用，例如CMA，per-device Coherent DMA的分配等，这时候，我们需要借用device tree的匹配机制进行这段保留内存的初始化动作。有兴趣的话可以看看RESERVEDMEM\_OF\_DECLARE的定义，这里就不再描述了。

6、通过命令行参数保留CMA内存

arm64\_memblock\_init--->dma\_contiguous\_reserve函数中会根据命令行参数进行CMA内存的保留，本文暂不描述之，留给CMA文档吧。

四、总结

物理内存布局是归于memblock模块进行管理的，该模块定义了struct memblock memblock这样的一个全局变量保存了memory type和reserved type的memory region list。而通过这两个memory region的数组，我们就知道了操作系统需要管理的所有系统内存的布局情况。

*原创文章，转发请注明出处。蜗窝科技*

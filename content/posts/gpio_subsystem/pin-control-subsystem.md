---
title: "linux内核中的GPIO系统之（2）：pin control subsystem"
date: 2014-07-26T18:24:15+08:00
url: "/gpio_subsystem/pin-control-subsystem.html"
gid: "69"
emlog_type: "blog"
summary: "\r\n\t在linux2.6内核上工作的嵌入式软件工程师在pin control上都会遇到这样的状况：\r\n\r\n\r\n\t（1）启动一个新的项目后，需要根\r\n据硬件平台的设定进行pin \r\ncontrol相关的编码。例如：在bootloader中建立一个大的table，描述各个引脚的配置和缺省状态。此外，由于SOC的引脚是可以复用\r\n的，因此在各个具体的driver中，也可能会对引脚进行的配置。这些工作都是"
author: "linuxer"
category: "GPIO子系统"
category_alias: "gpio_subsystem"
tags: ["pin", "control"]
views: 124885
comment_count: 43
aliases:
  - "/gpio_subsystem/69.html"
  - "/69.html"
---

一、前言

在linux2.6内核上工作的嵌入式软件工程师在pin control上都会遇到这样的状况：

（1）启动一个新的项目后，需要根据硬件平台的设定进行pin control相关的编码。例如：在bootloader中建立一个大的table，描述各个引脚的配置和缺省状态。此外，由于SOC的引脚是可以复用的，因此在各个具体的driver中，也可能会对引脚进行的配置。这些工作都是比较繁琐的工作，需要极大的耐心和细致度。

（2）发现某个driver不能正常工作，辛辛苦苦debug后发现仅仅是因为其他的driver在初始化的过程中修改了引脚的配置，导致自己的driver无法正常工作

（3）即便是主CPU是一样的项目，但是由于外设的不同，我们也不能使用一个kernel image，而是必须要修改代码（这些代码主要是board-specific startup code）

（4）代码不是非常的整洁，cut-and-pasted代码满天飞，linux中的冗余代码太多

作为一个嵌入式软件工程师，项目做多了，接触的CPU就多了，摔的跤就多了，之后自然会去思考，我们是否可以解决上面的问题呢？此外，对于基于ARM core那些SOC，虽然表面上看起来各个SOC各不相同，但是在pin control上还有很多相同的内容的，是否可以把它抽取出来，进行进一步的抽象呢？新版本中的内核（本文以3.14版本内核为例）提出了pin control subsystem来解决这些问题。

二、pin control subsystem的文件列表

1、源文件列表

我们整理linux/drivers/pinctrl目录下pin control subsystem的源文件列表如下：

|  |  |
| --- | --- |
| 文件名 | 描述 |
| core.c core.h | pin control subsystem的core driver |
| pinctrl-utils.c pinctrl-utils.h | pin control subsystem的一些utility接口函数 |
| pinmux.c pinmux.h | pin control subsystem的core driver(pin muxing部分的代码，也称为pinmux driver) |
| pinconf.c pinconf.h | pin control subsystem的core driver(pin config部分的代码，也称为pin config driver) |
| devicetree.c devicetree.h | pin control subsystem的device tree代码 |
| pinctrl-xxxx.c | 各种pin controller的low level driver。 |

在[pin controller driver](/gpio_subsystem/pin-controller-driver.html)文档中 ，我们以2416的pin controller为例，描述了一个具体的low level的driver，这个driver涉及的文件包括pinctrl-samsung.c，pinctrl-samsung.h和pinctrl-s3c24xx.c。

2、和其他内核模块接口头文件

很多内核的其他模块需要用到pin control subsystem的服务，这些头文件就定义了pin control subsystem的外部接口以及相关的数据结构。我们整理linux/include/linux/pinctrl目录下pin control subsystem的外部接口头文件列表如下：

|  |  |
| --- | --- |
| 文件名 | 描述 |
| consumer.h | 其他的driver要使用pin control subsystem的下列接口：    a、设置引脚复用功能    b、配置引脚的电气特性    这时候需要include这个头文件 |
| devinfo.h | 这是for linux内核的驱动模型模块（driver model）使用的接口。struct device中包括了一个struct dev\_pin\_info \*pins的成员，这个成员描述了该设备的引脚的初始状态信息，在probe之前，driver model中的core driver在调用driver的probe函数之前会先设定pin state |
| machine.h | 和machine模块的接口。 |

3、Low level pin controller driver接口

我们整理linux/include/linux/pinctrl目录下pin control subsystem提供给底层specific pin controller driver的头文件列表如下：

|  |  |
| --- | --- |
| 文件名 | 描述 |
| pinconf-generic.h | 这个接口主要是提供给各种pin controller driver使用的，不是外部接口。 |
| pinconf.h | pin configuration 接口 |
| pinctrl-state.h | pin control state状态定义 |
| pinmux.h | pin mux function接口 |

三、pin control subsystem的软件框架图

1、功能和接口概述

一般而言，学习复杂的软件组件或者软件模块是一个痛苦的过程。我们可以把我们要学习的那个软件block看成一个黑盒子，不论里面有多么复杂，第一步总是先了解其功能和外部接口特性。如果你愿意，你可以不去看其内部实现，先自己思考其内部逻辑，并形成若干问题，然后带着这些问题去看代码，往往事半功倍。

（1）、功能规格。pin control subsystem的主要功能包括：

（A）管理系统中所有可以控制的pin。在系统初始化的时候，枚举所有可以控制的pin，并标识这些pin。

（B）管理这些pin的复用（Multiplexing）。对于SOC而言，其引脚除了配置成普通GPIO之外，若干个引脚还可以组成一个pin group，形成特定的功能。例如pin number是{ 0, 8, 16, 24 }这四个引脚组合形成一个pin group，提供SPI的功能。pin control subsystem要管理所有的pin group。

（C）配置这些pin的特性。例如配置该引脚上的pull-up/down电阻，配置drive strength等

（2）接口规格。linux内核的某个软件组件必须放回到linux系统中才容易探讨它的接口以及在系统中的位置，因此，在本章的第二节会基于系统block上描述各个pin control subsystem和其他内核模块的接口。

（3）内部逻辑。要研究一个subsystem的内部逻辑，首先要打开黑盒子，细分模块，然后针对每一个模块进行功能分析、外部接口分析、内部逻辑分析。如果模块还是比较大，难于掌握，那么就继续细分，拆成子模块，重复上面的分析过程。在本章的第三节中，我们打开pin control subsystem的黑盒子进行进一步的分析。

2、pin control subsystem在和其他linux内核模块的接口关系图如下图所示：

[![pcb](/content/uploadfile/201407/ed00896a96bea67a76b5d8a901aee43320140726102404.gif "pcb")](/content/uploadfile/201407/c3dde08394d41eabca04b602d278db1620140726102402.gif)

pin control subsystem会向系统中的其他driver提供接口以便进行该driver的pin config和pin mux的设定，这部分的接口在第四章描述。理想的状态是GPIO controll driver也只是象UART,SPI这样driver一样和pin control subsystem进行交互，但是，实际上由于各种源由（后文详述），pin control subsystem和GPIO subsystem必须有交互，这部分的接口在第五章描述。第六章描述了Driver model和pin control subsystem的接口，第七章描述了为Pin control subsystem提供database支持的Device Tree和Machine driver的接口。

3、pin control subsystem内部block diagram

[![pccore](/content/uploadfile/201407/07edbb347ae8fb535f78f09a782bd36e20140726102406.gif "pccore")](/content/uploadfile/201407/e9243f9b8a8b5550b7a0816b59ac4c0820140726102405.gif)

起始理解了接口部分内容，阅读和解析pin control subsystem的内部逻辑已经很简单，本文就不再分析了。

四、pin control subsystem向其他driver提供的接口

当你准备撰写一个普通的linux driver（例如串口驱动）的时候，你期望pin control subsystem提供的接口是什么样子的？简单，当然最好是简单的，最最好是没有接口，当然这是可能的，具体请参考第六章的接口。

1、概述

普通driver调用pin control subsystem的主要目标是：

（1）设定该设备的功能复用。设定设备的功能复用需要了解两个概念，一个是function，另外一个pin group。function是功能抽象，对应一个HW逻辑block，例如SPI0。虽然给定了具体的gunction name，我们并不能确定其使用的pins的情况。例如：为了设计灵活，芯片内部的SPI0的功能可能引出到pin group { A8, A7, A6, A5 }，也可能引出到另外一个pin group{ G4, G3, G2, G1 }，但毫无疑问，这两个pin group不能同时active，毕竟芯片内部的SPI0的逻辑功能电路只有一个。 因此，只有给出function selector（所谓selector就是一个ID或者index）以及function的pin group selector才能进行function mux的设定。

（2）设定该device对应的那些pin的电气特性。

此外，由于电源管理的要求，某个device可能处于某个电源管理状态，例如idle或者sleep，这时候，属于该device的所有的pin就会需要处于另外的状态。综合上述的需求，我们把定义了pin control state的概念，也就是说设备可能处于非常多的状态中的一个，device driver可以切换设备处于的状态。为了方便管理pin control state，我们又提出了一个pin control state holder的概念，用来管理一个设备的所有的pin control状态。因此普通driver调用pin control subsystem的接口从逻辑上将主要是：

（1）获取pin control state holder的句柄

（2）设定pin control状态

（3）释放pin control state holder的句柄

pin control state holder的定义如下：

> struct pinctrl {   
> struct list\_head node;－－系统中的所有device的pin control state holder被挂入到了一个全局链表中   
> struct device \*dev;－－－该pin control state holder对应的device   
> struct list\_head states;－－－－该设备的所有的状态被挂入到这个链表中   
> struct pinctrl\_state \*state;－－－当前的pin control state   
> struct list\_head dt\_maps;－－－－mapping table   
> struct kref users;－－－－－－reference count   
> };

系统中的每一个需要和pin control subsystem进行交互的设备在进行设定之前都需要首先获取这个句柄。而属于该设备的所有的状态都是挂入到一个链表中，链表头就是pin control state holder的states成员，一个state的定义如下：

> struct pinctrl\_state {   
> struct list\_head node;－－－挂入链表头的节点   
> const char \*name;－－－－－该state的名字   
> struct list\_head settings;－－－属于该状态的所有的settings   
> };

一个pin state包含若干个setting，所有的settings被挂入一个链表中，链表头就是pin state中的settings成员，定义如下：

> struct pinctrl\_setting {   
> struct list\_head node;   
> enum pinctrl\_map\_type type;   
> struct pinctrl\_dev \*pctldev;   
> const char \*dev\_name;   
> union {   
> struct pinctrl\_setting\_mux mux;   
> struct pinctrl\_setting\_configs configs;   
> } data;   
> };

当driver设定一个pin state的时候，pin control subsystem内部会遍历该state的settings链表，将一个一个的setting进行设定。这些settings有各种类型，定义如下：

> enum pinctrl\_map\_type {   
> PIN\_MAP\_TYPE\_INVALID,   
> PIN\_MAP\_TYPE\_DUMMY\_STATE,   
> PIN\_MAP\_TYPE\_MUX\_GROUP,－－－功能复用的setting   
> PIN\_MAP\_TYPE\_CONFIGS\_PIN,－－－－设定单一一个pin的电气特性   
> PIN\_MAP\_TYPE\_CONFIGS\_GROUP,－－－－设定单pin group的电气特性   
> };

有pin mux相关的设定（PIN\_MAP\_TYPE\_MUX\_GROUP），定义如下：

> struct pinctrl\_setting\_mux {   
> unsigned group;－－－－－－－－该setting所对应的group selector   
> unsigned func;－－－－－－－－－该setting所对应的function selector   
> };

有了function selector以及属于该functiong的roup selector就可以进行该device和pin mux相关的设定了。设定电气特性的settings定义如下：

> struct pinctrl\_map\_configs {   
> const char \*group\_or\_pin;－－－－该pin或者pin group的名字   
> unsigned long \*configs;－－－－要设定的值的列表。这个值被用来写入HW   
> unsigned num\_configs;－－－－列表中值的个数   
> };

2、具体的接口

（1）devm\_pinctrl\_get和pinctrl\_get。devm\_pinctrl\_get是Resource managed版本的pinctrl\_get，核心还是pinctrl\_get函数。这两个接口都是获取设备（设备模型中的struct device）的pin control state holder（struct pinctrl）。pin control state holder不是静态定义的，一般在第一次调用该函数的时候会动态创建。创建一个pin control state holder是一个大工程，我们分析一下这段代码：

> static struct pinctrl \*create\_pinctrl(struct device \*dev)   
> {
>
> 分配pin control state holder占用的内存并初始化   
> p = kzalloc(sizeof(\*p), GFP\_KERNEL);   
> p->dev = dev;   
> INIT\_LIST\_HEAD(&p->states);   
> INIT\_LIST\_HEAD(&p->dt\_maps);
>
> mapping table这个database的建立也是动态的，当第一次调用pin control state holder的get函数的时候，就会通过调用pinctrl\_dt\_to\_map来建立该device需要的mapping entry。具体请参考第七章。
>
> ret = pinctrl\_dt\_to\_map(p);
>
> devname = dev\_name(dev);
>
> mutex\_lock(&pinctrl\_maps\_mutex);   
> for\_each\_maps(maps\_node, i, map) {   
> /\* Map must be for this device \*/   
> if (strcmp(map->dev\_name, devname))   
> continue;
>
> ret = add\_setting(p, map);－－－－分析一个mapping entry，把这个setting的代码加入到holder中   
>   
> }   
> mutex\_unlock(&pinctrl\_maps\_mutex);
>
> kref\_init(&p->users);
>
> /\* 把这个新增加的pin control state holder加入到全局链表中 \*/   
> mutex\_lock(&pinctrl\_list\_mutex);   
> list\_add\_tail(&p->node, &pinctrl\_list);   
> mutex\_unlock(&pinctrl\_list\_mutex);
>
> return p;   
> }

（2）devm\_pinctrl\_put和pinctrl\_put。是（1）接口中的逆函数。devm\_pinctrl\_get和pinctrl\_get获取句柄的时候申请了很多资源，在devm\_pinctrl\_put和pinctrl\_put可以释放。需要注意的是多次调用get函数不会重复分配资源，只会reference count加一，在put中referrenct count减一，当count＝＝0的时候才释放该device的pin control state holder持有的所有资源。

（3）pinctrl\_lookup\_state。根据state name在pin control state holder找到对应的pin control state。具体的state是各个device自己定义的，不过pin control subsystem自己定义了一些标准的pin control state，定义在pinctrl-state.h文件中：

> #define PINCTRL\_STATE\_DEFAULT "default"   
> #define PINCTRL\_STATE\_IDLE "idle"   
> #define PINCTRL\_STATE\_SLEEP "sleep"

（4）pinctrl\_select\_state。设定一个具体的pin control state接口。

五、和GPIO subsystem交互

1、为何pin control subsystem要和GPIO subsystem交互？

作为软件工程师，我们期望的硬件设计应该如下图所示：[![pin hw](/content/uploadfile/201407/9fe19d33cc038fdcfe089f7e9b1cdde820140726102409.gif "pin hw")](/content/uploadfile/201407/81200f2fcdc7db5873e5c3999f256bda20140726102408.gif)

GPIO的HW block应该和其他功能复用的block是对等关系的，它们共同输入到一个复用器block，这个block的寄存器控制哪一个功能电路目前是active的。pin configuration是全局的，不论哪种功能是active的，都可以针对pin进行电气特性的设定。这样的架构下，上图中红色边框的三个block是完全独立的HW block，其控制寄存器在SOC datasheet中应该是分成三个章节描述，同时，这些block的寄存器应该分别处于不同的地址区间。

对于软件工程师，我们可以让pin control subsystem和GPIO subsystem完全独立，各自进行初始化，各自映射自己的寄存器地址空间，对于pin control subsystem而言，GPIO和其他的HW block没有什么不同，都是使用自己提供服务的一个软件模块而已。然而实际上SOC的设计并非总是向软件工程师期望的那样，有的SOC的设计框架图如下：

[![pin hw2](/content/uploadfile/201407/e484edb990ef580db6d9fcee2a6ff08020140726102412.gif "pin hw2")](/content/uploadfile/201407/4a6a546b719573e2f6999ff0d4357ba920140726102411.gif)

这时候，GPIO block是alway active的，而红色边框的三个block是紧密的捆绑在一起，它们的寄存器占据了一个memory range（datasheet中用一个章节描述这三个block）。这时候，对于软件工程师来说就有些纠结了，本来不属于我的GPIO控制也被迫要参与进来。这时候，硬件寄存器的控制都是pin controller来处理，GPIO相关的操作都要经过pin controller driver，这时候，pin controller driver要作为GPIO driver的back-end出现。

2、具体的接口形态

（1）pinctrl\_request\_gpio。该接口主要用来申请GPIO。GPIO也是一种资源，使用前应该request，使用完毕后释放。具体的代码如下：

> int pinctrl\_request\_gpio(unsigned gpio)－－－－这里传入的是GPIO 的ID   
> {   
> struct pinctrl\_dev \*pctldev;   
> struct pinctrl\_gpio\_range \*range;   
> int ret;   
> int pin;
>
> ret = pinctrl\_get\_device\_gpio\_range(gpio, &pctldev, &range);－－－A   
> if (ret) {   
> if (pinctrl\_ready\_for\_gpio\_range(gpio))   
> ret = 0;   
> return ret;   
> }
>
> mutex\_lock(&pctldev->mutex);   
> pin = gpio\_to\_pin(range, gpio); －－－将GPIO ID转换成pin ID
>
> ret = pinmux\_request\_gpio(pctldev, range, pin, gpio); －－－－－－B
>
> mutex\_unlock(&pctldev->mutex);
>
> return ret;   
> }

毫无疑问，申请GPIO资源本应该是GPIO subsystem的责任，但是由于上一节描述的源由，pin control subsystem提供了这样一个接口函数供GPIO driver使用（其他的内核driver不应该调用，它们应该使用GPIO subsystem提供的接口）。多么丑陋的代码，作为pin control subsystem，除了维护pin space中的ID，还要维护GPIO 的ID以及pin ID和GPIO ID的关系。

A：根据GPIO ID找到该ID对应的pin control device（struct pinctrl\_dev）和GPIO rang（pinctrl\_gpio\_range）。在core driver中，每个low level的pin controller device都被映射成一个struct pinctrl\_dev，并形成链表，链表头就是pinctrldev\_list。由于实际的硬件设计（例如GPIO block被分成若干个GPIO 的bank，每个bank就对应一个HW GPIO Controller Block），一个pin control device要管理的GPIO ID是分成区域的，每个区域用struct pinctrl\_gpio\_range来抽象，在low level 的pin controller初始化的时候（具体参考samsung\_pinctrl\_register的代码），会调用pinctrl\_add\_gpio\_range将每个GPIO bank表示的gpio range挂入到pin control device的range list中（gpio\_ranges成员）。pinctrl\_gpio\_range 的定义如下：

> struct pinctrl\_gpio\_range {   
> struct list\_head node;   
> const char \*name;   
> unsigned int id;－－－－－－－－－－－GPIO chip ID   
> unsigned int base;－－－－－－该range中的起始GPIO IDD   
> unsigned int pin\_base;－－－在线性映射的情况下，这是起始的pin base   
> unsigned const \*pins;－－－在非线性映射的时候，这是table是pin到GPIO的lookup table   
> unsigned int npins;－－－－这个range有多少个GPIO引脚   
> struct gpio\_chip \*gc;------每个GPIO bank都是一个gpio chip，对应一个GPIO range   
> };

pin ID和GPIO ID有两种映射关系，一种是线性映射（这时候pin\_base有效），也就是说，对于这个GPIO range，GPIO base ID是a，pin ID base是b，那么a<--->b，a＋1<--->b＋1，a＋2<--->b＋2，以此类推。对于非线性映射（pin\_base无效，pins是有效的），我们需要建立一个lookup table，以GPIO ID为索引，可以找到对于的pin ID。

B：这里主要是进行复用功能的设定，毕竟GPIO也是引脚的一个特定的功能。pinmux\_request\_gpio函数的作用主要有两个，一个是在core driver中标记该pin已经用作GPIO了，这样，如果有模块后续request该资源，那么core driver可以拒绝不合理的要求。第二步就是调用底层pin controller driver的callback函数，进行底层寄存器相关的操作。

（2）pinctrl\_free\_gpio。有申请就有释放，这是pinctrl\_request\_gpio的逆函数

（3）pinctrl\_gpio\_direction\_input和pinctrl\_gpio\_direction\_output。为已经指定为GPIO功能的引脚设定方向，输入或者输出。代码很简单，不再赘述。

六、和驱动模型的接口

前文已经表述过，最好是让统一设备驱动模型（Driver model）来处理pin 的各种设定。与其自己写代码调用devm\_pinctrl\_get、pinctrl\_lookup\_state、pinctrl\_select\_state等pin control subsystem的接口函数，为了不让linux内核自己的框架处理呢。本章将分析具体的代码，这些代码实例对自己driver调用pin control subsystem的接口函数来设定本device的pin control的相关设定也是有指导意义的。 linux kernel中的驱动模型提供了driver和device的绑定机制，一旦匹配会调用probe函数如下：

> static int really\_probe(struct device \*dev, struct device\_driver \*drv)   
> {   
> ……   
> ret = pinctrl\_bind\_pins(dev); －－－对该device涉及的pin进行pin control相关设定   
> ……
>
> if (dev->bus->probe) {－－－－－－下面是真正的probe过程   
> ret = dev->bus->probe(dev);   
> if (ret)   
> goto probe\_failed;   
> } else if (drv->probe) {   
> ret = drv->probe(dev);   
> if (ret)   
> goto probe\_failed;   
> }
>
> ……
>
> }

pinctrl\_bind\_pins的代码如下：

> int pinctrl\_bind\_pins(struct device \*dev)   
> {   
> int ret;
>
> dev->pins = devm\_kzalloc(dev, sizeof(\*(dev->pins)), GFP\_KERNEL);－－－（1）
>
> dev->pins->p = devm\_pinctrl\_get(dev);－－－－－－－－－－－－－－－－－（2）
>
> dev->pins->default\_state = pinctrl\_lookup\_state(dev->pins->p, －－－－－－－（3）   
> PINCTRL\_STATE\_DEFAULT);
>
> ret = pinctrl\_select\_state(dev->pins->p, dev->pins->default\_state); －－－－－（4）
>
> dev->pins->sleep\_state = pinctrl\_lookup\_state(dev->pins->p, －－－－－－（3）   
> PINCTRL\_STATE\_SLEEP);
>
> dev->pins->idle\_state = pinctrl\_lookup\_state(dev->pins->p, －－－－－－－（3）   
> PINCTRL\_STATE\_IDLE);
>
> return 0;   
> }

（1）struct device数据结构有一个pins的成员，它描述了和该设备相关的pin control的信息，定义如下：

> struct dev\_pin\_info {   
> struct pinctrl \*p;－－－－－－－－－－－－该device对应的pin control state holder   
> struct pinctrl\_state \*default\_state;－－－－缺省状态   
> struct pinctrl\_state \*sleep\_state;－－－－－电源管理相关的状态   
> struct pinctrl\_state \*idle\_state;－－－－－电源管理相关的状态   
> };

（2）调用devm\_pinctrl\_get获取该device对应的 pin control state holder句柄。

（3）搜索default state，sleep state，idle state并记录在本device中

（3）将该设备设定为pin default state

七、和device tree或者machine driver相关的接口

1、概述

device tree或者machine driver这两个模块主要是为 pin control subsystem提供pin mapping database的支持。这个database的每个entry用下面的数据结构表示：

> struct pinctrl\_map {   
> const char \*dev\_name;－－－使用这个mapping entry的设备名   
> const char \*name;－－－－－－该名字表示了该mapping entry   
> enum pinctrl\_map\_type type;－－－这个entry的mapping type   
> const char \*ctrl\_dev\_name; －－－－－pin controller这个设备的名字   
> union {   
> struct pinctrl\_map\_mux mux;   
> struct pinctrl\_map\_configs configs;   
> } data;   
> };

2、通过machine driver静态定义的数据来建立pin mapping database

machine driver定义一个巨大的mapping table，描述，然后在machine初始化的时候，调用pinctrl\_register\_mappings将该table注册到pin control subsystem中。

3、通过device tree来建立pin mapping database

pin mapping信息定义在dts中，主要包括两个部分，一个是定义在各个具体的device node中，另外一处是定义在pin controller的device node中。

一个典型的device tree中的外设node定义如下（建议先看看[pin controller driver](/gpio_subsystem/pin-controller-driver.html)的第二章关于dts的描述）：

> device-node-name {   
> 定义该device自己的属性
>
> pinctrl-names = "sleep", "default";   
> pinctrl-0 = ;   
> pinctrl-1 = ;   
> };

对普通device的dts分析在函数pinctrl\_dt\_to\_map中，代码如下：

> int pinctrl\_dt\_to\_map(struct pinctrl \*p)   
> {   
> of\_node\_get(np);   
> for (state = 0; ; state++) {－－－－－－－－－－－－－－－－－－－（1）   
> /\* Retrieve the pinctrl-\* property \*/   
> propname = kasprintf(GFP\_KERNEL, "pinctrl-%d", state);   
> prop = of\_find\_property(np, propname, &size);   
> kfree(propname);   
> if (!prop)   
> break;   
> list = prop->value;   
> size /= sizeof(\*list); －－－－－－－－－－－－－－（2）
>
> /\* Determine whether pinctrl-names property names the state \*/   
> ret = of\_property\_read\_string\_index(np, "pinctrl-names", －－－－－－（3）   
> state, &statename);   
>   
> if (ret < 0) {   
> /\* strlen("pinctrl-") == 8 \*/   
> statename = prop->name + 8; －－－－－－－－－－－－－（4）   
> }
>
> /\* For every referenced pin configuration node in it \*/   
> for (config = 0; config < size; config++) { －－－－－－－－－－－（5）   
> phandle = be32\_to\_cpup(list++);
>
> /\* Look up the pin configuration node \*/   
> np\_config = of\_find\_node\_by\_phandle(phandle); －－－－－－（6）
>
> /\* Parse the node \*/   
> ret = dt\_to\_map\_one\_config(p, statename, np\_config); －－－－（7）   
> of\_node\_put(np\_config);   
> if (ret < 0)   
> goto err;   
> }
>
> /\* No entries in DT? Generate a dummy state table entry \*/   
> if (!size) {   
> ret = dt\_remember\_dummy\_state(p, statename); －－－－－－－（8）   
> if (ret < 0)   
> goto err;   
> }   
> }
>
> return 0;
>
> err:   
> pinctrl\_dt\_free\_maps(p);   
> return ret;   
> }

（1）pinctrl-0 pinctrl-1 pinctrl-2……表示了该设备的一个个的状态，这里我们定义了两个pinctrl-0和pinctrl-1分别对应sleep和default状态。这里每次循环分析一个pin state。

（2）代码执行到这里，size和list分别保存了该pin state中所涉及pin configuration phandle的数目以及phandle的列表

（3）读取从pinctrl-names属性中获取state name

（4）如果没有定义pinctrl-names属性，那么我们将pinctrl-0 pinctrl-1 pinctrl-2……中的那个ID取出来作为state name

（5）遍历一个pin state中的pin configuration list，这里的pin configuration实际应该是pin controler device node中的sub node，用phandle标识。

（6）用phandle作为索引，在device tree中找他该phandle表示的那个pin configuration

（7）分析一个pin configuration，具体下面会仔细分析

（8）如果该设备没有定义pin configuration，那么也要创建一个dummy的pin state。

这里我们已经进入对pin controller node下面的子节点的分析过程了。分析一个pin configuration的代码如下：

> static int dt\_to\_map\_one\_config(struct pinctrl \*p, const char \*statename,   
> struct device\_node \*np\_config)   
> {   
> struct device\_node \*np\_pctldev;   
> struct pinctrl\_dev \*pctldev;   
> const struct pinctrl\_ops \*ops;   
> int ret;   
> struct pinctrl\_map \*map;   
> unsigned num\_maps;
>
> /\* Find the pin controller containing np\_config \*/   
> np\_pctldev = of\_node\_get(np\_config);   
> for (;;) {   
> np\_pctldev = of\_get\_next\_parent(np\_pctldev);－－－－－－－（1）   
> if (!np\_pctldev || of\_node\_is\_root(np\_pctldev)) {   
> of\_node\_put(np\_pctldev);   
> return -EPROBE\_DEFER;   
> }   
> pctldev = get\_pinctrl\_dev\_from\_of\_node(np\_pctldev);－－－－－（2）   
> if (pctldev)   
> break;－－－－－－－－－－－－－－－－－－－－－－－－（3）   
> /\* Do not defer probing of hogs (circular loop) \*/   
> if (np\_pctldev == p->dev->of\_node) {   
> of\_node\_put(np\_pctldev);   
> return -ENODEV;   
> }   
> }   
> of\_node\_put(np\_pctldev);
>
> /\*   
> \* Call pinctrl driver to parse device tree node, and   
> \* generate mapping table entries   
> \*/   
> ops = pctldev->desc->pctlops;   
> ret = ops->dt\_node\_to\_map(pctldev, np\_config, &map, &num\_maps);－－－－（4）   
> if (ret < 0)   
> return ret;
>
> /\* Stash the mapping table chunk away for later use \*/   
> return dt\_remember\_or\_free\_map(p, statename, pctldev, map, num\_maps);－－－－（5）   
> }

（1）首先找到该pin configuration node对应的parent node（也就是pin controler对应的node），如果找不到或者是root node，则进入出错处理。

（2）获取pin control class device

（3）一旦找到pin control class device则跳出for循环

（4）调用底层的callback函数处理pin configuration node。这也是合理的，毕竟很多的pin controller bindings是需要自己解析的。

（5）将该pin configuration node的mapping entry信息注册到系统中

八、core driver和low level pin controller driver的接口规格

pin controller描述符。每一个特定的pin controller都用一个struct pinctrl\_desc来抽象，具体如下：

> struct pinctrl\_desc {   
> const char \*name;   
> struct pinctrl\_pin\_desc const \*pins;   
> unsigned int npins;   
> const struct pinctrl\_ops \*pctlops;   
> const struct pinmux\_ops \*pmxops;   
> const struct pinconf\_ops \*confops;   
> struct module \*owner;   
> };

pin controller描述符需要描述它可以控制多少个pin（成员npins），每一个pin的信息为何？（成员pins）。这两个成员就确定了一个pin controller所能控制的引脚的信息。

pin controller描述符中包括了三类操作函数：pctlops是一些全局的控制函数，pmxops是复用引脚相关的操作函数，confops操作函数是用来配置引脚的特性（例如：pull-up/down）。struct pinctrl\_ops中各个callback函数的具体的解释如下：

|  |  |
| --- | --- |
| callback函数 | 描述 |
| get\_groups\_count | 该pin controller支持多少个pin group。pin group的定义可以参考本文关于pin controller的功能规格中的描述。注意不要把pin group和IO port的硬件分组搞混了。例如：S3C2416有138个I/O 端口，分成11组，分别是gpa～gpl，这个组并不叫pin group，而是叫做pin bank。pin group是和特定功能（例如SPI、I2C）相关的一组pin。 |
| get\_group\_name | 给定一个selector（index），获取指定pin group的name |
| get\_group\_pins | 给定一个selector（index），获取该pin group中pin的信息（该pin group包括多少个pin，每个pin的ID是什么） |
| pin\_dbg\_show | debug fs的callback接口 |
| dt\_node\_to\_map | 分析一个pin configuration node并把分析的结果保存成mapping table entry，每一个entry表示一个setting（一个功能复用设定，或者电气特性设定） |
| dt\_free\_map | 上面函数的逆函数 |

复用引脚相关的操作函数的具体解释如下：

|  |  |
| --- | --- |
| call back函数 | 描述 |
| request | pin control core进行具体的复用设定之前需要调用该函数，主要是用来请底层的driver判断某个引脚的复用设定是否是OK的。 |
| free | 是request的逆函数。调用request函数请求占用了某些pin的资源，调用free可以释放这些资源 |
| get\_functions\_count | 就是返回pin controller支持的function的数目 |
| get\_function\_name | 给定一个selector（index），获取指定function的name |
| get\_function\_groups | 给定一个selector（index），获取指定function的pin groups信息 |
| enable | enable一个function。当然要给出function selector和pin group的selector |
| disable | enable的逆函数 |
| gpio\_request\_enable | request并且enable一个单独的gpio pin |
| gpio\_disable\_free | gpio\_request\_enable的逆函数 |
| gpio\_set\_direction | 设定GPIO方向的回调函数 |

配置引脚的特性的struct pinconf\_ops数据结构的各个成员定义如下：

|  |  |
| --- | --- |
| call back函数 | 描述 |
| pin\_config\_get | 给定一个pin ID以及config type ID，获取该引脚上指定type的配置。 |
| pin\_config\_set | 设定一个指定pin的配置 |
| pin\_config\_group\_get | 以pin group为单位，获取pin上的配置信息 |
| pin\_config\_group\_set | 以pin group为单位，设定pin group的特性配置 |
| pin\_config\_dbg\_parse\_modify | debug接口 |
| pin\_config\_dbg\_show | debug接口 |
| pin\_config\_group\_dbg\_show | debug接口 |
| pin\_config\_config\_dbg\_show | debug接口 |

原创文章，转发请注明出处。蜗窝科技。[/gpio_subsystem/pin-control-subsystem.html](/gpio_subsystem/pin-control-subsystem.html "/gpio_subsystem/pin-control-subsystem.html")

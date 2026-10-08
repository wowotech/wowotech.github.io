---
title: "SDRAM Internals"
date: 2014-05-14T16:25:34+08:00
url: "/basic_tech/sdram-internals.html"
gid: "41"
emlog_type: "blog"
summary: "\r\n\tSDRAM（synchronous dynamic random-access memory）是嵌入式系统中经常用到的器件。对于一个嵌入式软件工程师而言，了解SDRAM的机理是有益的。我们可以从下面三个方面理解SDRAM：\r\n\r\n\r\n\t1、RAM很好理解，就是可以随机存取的memory。\r\n\r\n\r\n\t2、\r\ndynamic 是和static对应的，SRAM就是static random-ac"
author: "linuxer"
category: "基础技术"
category_alias: "basic_tech"
tags: ["SDRAM"]
views: 34539
comment_count: 39
aliases:
  - "/basic_tech/41.html"
  - "/41.html"
---

一、简介

SDRAM（synchronous dynamic random-access memory）是嵌入式系统中经常用到的器件。对于一个嵌入式软件工程师而言，了解SDRAM的机理是有益的。我们可以从下面三个方面理解SDRAM：

1、RAM很好理解，就是可以随机存取的memory。

2、dynamic 是和static对应的，SRAM就是static random-access memory。SRAM和DRAM（dynamic random-access memory）都是由若干能够保存0和1两种状态的cell组成。对于SRAM，只要保持芯片的供电，其cell就可以保存0或者1的信息。但是对于DRAM而言，其bit信息是用电容来保存的（charged or not charged）。由于有漏电流，因此DRAM中的bit信息只能保持若干个毫秒。这个时间听起来很短，但是对于以ns计时的CPU而言已经是足够的长了，因此，只要及时刷新（refresh，术语总是显得高大上，通俗讲就是读出来再写进去）DRAM，信息就可以长久的保存了。

3、synchronous 是和asynchronous 对应的。synchronous是一个有多种含义的词汇，对于硬件芯片这个场景，主要是说芯片的行为动作是在一个固定的clock信号的驱动下工作。对于电路设计而言，synchronous 简单但是速度慢，功耗大。asynchronous 则相反，在设计过程中需要考虑复杂的race condition的问题，其速度快，理论上只是受限于逻辑门（logic gate）的propagation delay。

1968年，Dennard获得了DRAM的专利。随后，各大厂商和研究机构对DRAM进行了改进。例如增加了clock信号，让DRAM的电路设计变成synchronous 类型的。2000之后，由于其卓越的性能，SDRAM完全取代了DRAM的位置。随后的发展（DDR、DDR2和DDR3）并没有改变原理，只是速度上升了。因此，本文以SDR（Single Data Rate）SDRAM为例，讲述其内部机理。

二、SDRAM cell

一个SDRAM芯片有若干个cell组成，每个cell可以保存一个bit的信息。SDRAM cell如下图（注：该图片来自网络）所示：

[![dramcell](/content/uploadfile/201405/88d6907ae52987f9221fb71f38e9a5d220140514082524.gif "dramcell")](/content/uploadfile/201405/796f5447188b55500e48330aca5c290b20140514082522.gif)

电容Cs（电容的英文是Capacitor，s表示storage）的电荷状态（charged or discharged）可以表示0和1的信息。

首先我们看看如何向一个cell中写入数据。写入的数据体现在bit line的电平上，如果要写入1，那么将bit line设定为高电平Vs。如果写入0，那么将bit line设定为低电平。具体的写入动作体现在电路逻辑上就是对Cs进行充电或者放电。要完成这个操作需要将WL（word line）设置为高电平，以便让晶体管M1处于导通状态，这时候，Cs和bit line共享电荷了。对于写入1，Cs被充电，电压升到Vs。对于写入0，Cs被放电，电压为0。

数据读取要比数据写入复杂一些。假设该cell已经保存了一个bit的数据，我们打算将其读出来，那么需要首先将WL设置为高电平，以便让晶体管M1处于导通状态。这时候逻辑电路block可以通过BL（Bit line）感知电荷的重新分配（redistribution），从而确定Cell中保存的是0还是1。假设充满电荷的Cs表示1，其上的电压是Vs，如果保存了比特0，那么电容没有电荷，电压等于0。为了感知Cs的电荷情况，我们需要将BL上的电压提升到Vs/2。一旦M1处于导通状态，如果Cell中保存了比特1，那么由于电压差，电荷流出Cs导致Bit line上的电压升高，Cell之外的一个逻辑电路block（术语叫做Sense amplifier）可以感知这个变化，从而读出数据1。对于数据0也是一样，只不过电荷是流向Cs，bit line上的电压降低。总结一下，read sequece如下：

1、将BL上的电压提升到Vs/2

2、set WL high ，让M1处于导通状态

3、感知bit line的的电荷状态

4、write back。由于读出的操作是破坏性的（电荷的流出或者流入），因此读操作之后需要refresh。

三、SDRAM 芯片的组织

在了解了一个基本的cell组成之后，我们来看看这些基本的cell如何组织起来，完成数据存储。我们用Micro的64MB（512Mb）的Mobile LPSDR SDRAM MT48H32M16为例来描述SDRAM芯片的结构。我们先给出一些基本的描述（有些概念后续再定义）：512M个bit被分成了4个bank，每个bank有8M个supercell，每个supercell有16个cell组成。4x8Mx16＝512Mb。对于bank，其8M个supercell不是线性组合的，而是组成矩阵，通过Row address和Column address进行访问。组成示意图（注：该图片来自网络）如下：

[![dram-array](/content/uploadfile/201405/b328f24d70ac7b1335876db33e0bf07120140514082529.gif "dram-array")](/content/uploadfile/201405/5d58a7bda98d173a726c2ccd6a5d826720140514082526.gif)

一个bank是由若干逻辑电路block组成，具体包括存储阵列、Sense Amplifiers、Row Address Latch and Decoder、Column Address Latch and Decoder以及Data buffer &control。

对于计算机系统，我们不可能是一个bit一个bit的访问，一般而言，32 bit的CPU可能是按照Byte（8个bit）、short int（16个bit）或者int（32个bit）进行数据访问。基于这样的概念，我们提出一个supercell的概念（这个概念来自Computer System, A Programmer's Perspective）。对于MT48H32M16这颗chip，16个cell组成了一个supercell，其实也就是输出数据总线的宽度。一次SDRAM的访问最大可以输出16个bit。如果想要基于Byte的访问，那么需要CPU给出DQM信号，以便mask高8bit或者低8个bit。由此可见，在SDRAM内部，其寻址的最小单位是supercell。

访问super cell的时候需要raw address和column address。选中的supercall通过Data I/O buffer输出数据。对于MT48H32M16这颗chip，一个bank的supercell矩阵是由8196行，1024列组成。

一个SDRAM芯片是由一个或者多个bank再加上一些逻辑控制电路block组成。到底bank是个什么概念？为什么需要bank，或者说single bank和multi bank相比有什么差异。现代的SDRAM芯片的容量已经越来越大了，用单一一个supercell矩阵会带来成本、性能以及复杂度的问题。此外，需要指出的是多个bank上的操作是独立的，也就是说，一个bank上选中了一个Row，或者进行precharge的操作并不影响其他bank上的读写操作。这样并行的操作可以加快SDRAM的速度。

四、和SDRAM controller的连接

SDRAM和 SDRAM controller的连接信号如下表所示（具体的数据以MT48H32M16为例）：

|  |  |  |
| --- | --- | --- |
| signal name | direction | description |
| 地址线 | CPU输出到SDRAM芯片（下面简称输出） | CPU输出给SDRAM芯片的Row address和column address可以通过地址线输入。由于分成Row address和column address，地址线不需要那么多了。例如：64MB的RAM如果线性排列，需要26根地址线，由于是矩阵结构，Row address（8196行，13根地址线）和column address（1024，10根地址线）是复用的，因此只需要13根地址线就OK了 |
| BANK地址输入 | 输出 | 选择4个bank中的一个 |
| 数据线 | I/O | 16bit的数据输入输出信号线。在系统设计的时候，我们可以选择16bit或者32bit组织的SDRAM chip，不同的选择其实是在性能（32bit的要快一些，一次4B操作不需要分成两次访问了）和系统size（32bit占用了太多的I/O line，如果系统有太多的器件，那么pin assign非常困难，可能要引入I/O expander这样的器件）做平衡。 |
| DQM信号 | 输出 | Data Mask信号。32 bit的CPU访问memory的时候有1B、2B和4B的方式。当访问数据的宽度小于实际数据线的宽度的时候就需要data mask，将不需要的高（或者低）字节（或者16bit）mask掉。 |
| clock信号 | 输出 | 之所以是synchronous就是因为有clock作为节拍器，让SDRAM的每一步按照固定的节拍动作（在clock的positive edge上触发）。典型值是133M clock，每个clock是7.5 ns。当然，目前最快的DDR3的器件其clock可以达到800MHz了。 |
| CKE信号 | 输出 | clock enable信号。在有些电源管理状态下会控制该信号，以便获得更好的电源管理performance。为了完成数据传输，CKE信号需要enable，以便把来自SDRAM controller的clock信号传递给SDRAM内部的各个HW block。 |
| 片选信号 | 输出 | 低电平的时候选中该SDRAM芯片 |
| RAS,CAS,WE | 输出 | RAS（Row Address Strobe）和CAS（Column Address Strobe）表示地址线上的地址信号的类型，是Row address还是Column Address。WE的电平状态可以标识本次对SDRAM的操作是read还是write |

五、SDRAM Command

通过上面章节的signal，CPU（SDRAM controller）可以向SDRAM发送各种命令，具体什么样的信号状态组合形成什么样的命令可以参考芯片datasheet的True table，这里只是从功能层面介绍各个SDRAM command。SDRAM上的每一个bank都会维护一个状态机，如下：

[![STATE M](/content/uploadfile/201405/e7817c285e795aa1e6e2cf907beee70520140514082532.gif "STATE M")](/content/uploadfile/201405/0a0c36a7b7cad803280d2b9e38b66d3020140514082530.gif)

具体的命令解释如下：

1、ACTIVE。根据section 2中介绍的内容，要访问cell中bit的内容，必须先导通cell中的晶体管M1。ACTIVE命令就是干这个工作的。该命令需要携带bank address和Row address的参数，告知具体是要选择后续要访问哪一个bank的哪一行（后续要访问的具体数据的column地址在READ或者WRITE命令提供）。一个bank中，同一时间只能active（让该行的Word line设置为高电平，以便导通cell的晶体管）一行。如果想要发送ACTIVE命令去本bank中的另外一行，直接发送是不行的，必须要close（PRECHARGE）之前打开的那个行。如果想要发送ACTIVE命令去另外一个bank中的某一行则没有这个限制（要满足tRRD的要求），这种跨bank的访问可以减少访问行的开销。

2、PRECHARGE。从用户层面看，PRECHARGE命令就是DEACTIVE命令。ACTIVE命令打开某个bank中的一行（导通这一行所有cell的M1晶体管），以便后续访问具体某一个column的supercell的内容。但是一旦访问完成了，就需要关掉之前打开的那个行（如果不关，该行的所有cell的晶体管M1处于导通状态，那么电容上的数据是无法保存的，除非bit line处于高阻状态）。其实通常PRECHARGE不需要指定Row address，毕竟一个bank中，同一时间只能active一个行。因此，PRECHARGE命令有两种mode，一种是PRECHARGE一个bank，这时候需要携带bank address的参数；另外一种情况是PRECHARGE All bank，不需要携带bank address的参数，该命令会将所有bank上的active的行close掉。地址线的A10用来选择PRECHARGE All bank或者PRECHARGE specific bank。为什么可以复用A10地址线？因此发送PRECHARGE的时候一定是已经提供ACTIVE命令发送了Bank地址和Row地址，这时候，地址线只会使用A0～A9（MT48H32M16有1024个column，使用A0～A9这10条地址线就OK了）。

3、WRITE。WRITE命令会携带Column的地址，说明是对哪一个supercell进行操作。这时候，bank地址、Row 地址、Column地址都是ready的，选中的supercell中的data就会保存为data总线上的数据。除了column地址，WRITE命令还有一个参数就是是否进行auto precharge（通过A10进行选择）。如果auto precharge，完成WRITE操作后，会对本次操作涉及的行进行PRECHARGE的操作。如果没有选择auto precharge，那么完成WRITE操作后，该行保持打开，以便后后续对该行进行持续的访问。理解了这些基本的概念后，问题来了，如何配置auto precharge？在WRITE之后自己进行PRECHARGE也就是意味这close了当前的那一个Row，PRECHARGE命令之后，tRP时间之后，该行又可以接受下一次的访问（ACTIVE then READ or WRITE）。但是，如果下一次对数据的访问是和当前访问的数据在同一行的话，我们其实是不必PRECHARGE，直接进行访问就OK了，这样，数据访问速度会快些。

4、READ。和WRITE命令一样，READ命令也会携带Column的地址，说明是对哪一个supercell进行访问。这时候，bank地址、Row 地址、Column地址都是ready的，选中的supercell中的data就会反应到data总线上。auto precharge的设定和WRITE命令一样，这里不再赘述。

5、SDRAM芯片power on之后需要有一个Initialize的动作，init之后，状态机才会迁移到Idle状态。初始化过程中最重要的是LOAD MODE REGISTER。SDRAM controller和SDRAM进行通信，那么需要对通信参数进行沟通，大家都是按照同样的通信参数进行沟通，数据才会能正确的访问。这些参数包括Burst Length、CAS latency等（其他参数这里不再详细描述）。Burst length比较好理解，一次对SDRAM的访问是一个操作序列：ACTIVE--->READ/WRITE---->DATA0--->DATA1 …--->DATAn。Burst length描述了在这个序列中DATA的数目。burst length如何设定呢？其实这是和程序逻辑相关的，如果程序是顺序访问，毫无疑问，多个DATA可以节省命令序列带来的开销。如果程序是随机访问，那么一个burst的数据很多都是浪费的。由于局部性原理（好的程序需要有好的locality，也就是说cache friendly），当前的系统结构都是采用了cache，一般而言，cache line是32字节，那么如果burst length设定为32字节，那么，一次burst正好加载了一个cache line。CAS Latency的具体含义请参考section 6中关于timing参数的描述。

有些电源管理相关的command这里没有描述，具体请参考Section 七的描述。

六、SDRAM的timing

从软件角度来看，程序员需要对SDRAM controller的寄存器进行设定，而这些寄存器中，很大一部分是对SDRAM的timing参数进行设定，本节将重点描述SDRAM的timing参数。

1、CAS Latency的含义是这样的：在READ命令后就选定了列地址，这时候就已经确定了具体的存储单元，剩下的事情就是数据通过数据I/O 通道输出到数据总线上了。但是在READ命令发出之后，仍要经过一定的时间才能有数据输出，从READ命令发出到第一笔数据输出的这段时间被定义为CAS Latency。CAS Latency是和read操作的performance有关系。

2、tRAS参数。ACTIVE命令和PRECHARGE命令是一对相反的操作，这两个命令之间有一定的时序要求，就好比你让一个人向东跑，立刻又让他向西跑，人总是要反应时间的。硬件也一样，SDRAM在发送了ACTIVE命令后，需要在tRAS之后才能发送PRECHARGE命令。此外，这个参数也限制了self refresh命令和exit self refresh之间的时序，也就是说，在进入self refresh状态后，必须停留tRAS的时间段之后才能退出该状态。具体self refresh状态的含义请参考Section 7的描述。

3、WRITE recovery time（tWR）。数据总线的数据在锁定在SDRAM的Data buffer中后需要一定的时间写入到cell，这个时间就是WRITE recovery time，如果立刻发送PRECHARGE命令的话，数据可能来不及写入（发送PRECHARGE意味该row的晶体管M1截止状态，bit line和cell中的storage capacitor就不导通了）。因此SDRAM controller需要在tWR的时间之后才能发送PRECHARGE命令。

4、ACTIVE-to-READ or WRITE delay（tRCD）。在发送WRITE/READ命令之前需要先发送ACTIVE命令（select bank and activate row），这两个命令之间有一个时间间隔（这时候硬件需要进行Bank地址译码、Row address 译码、此外还包括晶体管的导通时间等），这个间隔被定义为tRCD，该参数和SDRAM的读写性能有关。

5、PRECHARGE command period（tRP）。发送PRECHARGE命令，关闭BANK中的Active的Row是需要时间的，tRP时间之后，硬件完成了相关动作，回到idle状态，这时候才可以后续发送Self refresh命令、Auto refresh命令或者发送ACTIVE命令进行数据的访问。

6、ACTIVE-to-ACTIVE command period（tRC）。这是向SDRAM的某一个bank连续发送ACTIVE命令的时间间隔要求。在发送了ACTIVE命令后，至少要经过tRAS之后才能发送PRECHAGE，而PRCHARGE也需要一定的时间（tRP），因此tRP ＋ tRAS >= tRC。

7、Refresh period（tREF）。对于SDRAM芯片，要不断进行刷新（Refresh）才能保留住数据（这也是和static RAM的本质区别），具体的刷新频率和实际的SDRAM chip相关，一般而言要64ms（或者更少的时间）内就要完成对bank内的所有的行数据的刷新动作。

8、AUTO REFRESH period（tRFC）。发送了AUTO REFRESH之后，SDRAM要对各个bank的各个Row进行refresh，这个需要一定的时间，这个时间段过后，SDRAM chip才会接收ACTIVE命令以便进行后续的数据访问。一般而言，SDRAM controller的寄存器中会有一个是和Auto Refresh设定相关的寄存器，假设Refresh period（tREF）是64mS，那么该寄存器的设定要保证SDRAM controller每64ms内要发起refresh的操作。

上面就是SDRAM的主要的timing参数，在具体设定的时候，要考虑SDRAM controller的clock以及具体SDRAM芯片的速度。一般而言，SDRAM的datasheet上会给出具体timing的要求，例如a ns，如果SDRAM Controller的clock是133MHz，也就是说一个clock是7.5ns，那么将a ns换算成整数个SDRAM clock，之后设定到SDRAM controller的寄存器就OK了。

七、SDRAM的电源管理

在进行电源管理之前，先了解一些基本概念的东西，也是AUTO REFRESH 和 SELF REFRESH的概念。本身Auto Refresh用于正常操作期间（AUTO REFRESH 其实和电源管理关系不大，但是和SELF REFRESH有点关系，因此这里一并谈谈），每隔一定的clock，SDRAM controller就会发起一个auto refresh的动作（多谢SDRAM controller，系统软件工程师不用关注这样的动作），在刷新过程中，所有对SDRAM的正常访问都不被允许，在tRFC之后就可进入正常的工作状态。而Self Refresh用于系统power down的时候，这时候，SDRAM controller不再提供clock信号（AUTO REFRESH 和SELF REFRESH在硬件信号上就差别在CKE信号上，SELF REFRESH的CKE是disable的），SDRAM芯片内部逻辑会启动对所有cell的刷新动作，从而保持SDRAM中的数据。

SDRAM的电源管理状态有以下三种：

1、Deep Power Down。SDRAM controller发送Deep Power Down命令可以将SDRAM芯片推送到一个极低功耗状态（约15uA）。这时候存储阵列的power会被shutdown，也就是意味着所有的数据是丢失掉了，这时候，mode register的设定是保持的。当从Deep Power Down退出的时候，需要对SDRAM芯片进行一个完整的初始化过程。

2、Power Down。在CKE是低电平的情况下，发送一个NOP或者INHIBIT命令就可以让SDRAM进入power down mode。Power Down有两种mode，一种叫做PRECHARGE POWER-DOWN，另外一种叫做ACTIVE POWER-DOWN。如果在所有bank都是idle状态下（没有打开的行）进入Power down mode，那么这种mode就叫做PRECHARGE POWER-DOWN（该状态的功耗大约是300uA）。如果在有打开行（active row）的情况下进入Power down mode，那么这种mode就叫做ACTIVE POWER-DOWN（该状态的功耗大约是6mA）。想让SDRAM芯片退出power down mode的时候，要拉高CKE信号，发送一个NOP或者INHIBIT命令就可以让SDRAM退出power down mode。为了进一步降低功耗，可以把SDRAM controller的clock输出disable掉（这时候CKE是disable的，即便是SDRAM controller产生了clock信号，SDRAM的内部逻辑电路也不会被驱动）。看起来一切都很美，问题来了，数据是否可以保持？很遗憾，超过了Refresh period（tREF）后，SDRAM中的数据就不会保持了。因此，为了保存数据，我们可以让SDRAM controller在auto refresh timer超时的时候退出power down mode，完成refresh的操作，之后，如果没有pending的数据，继续进入power down mode。

3、Self Refresh。这种mode的功耗在1mA以下。在这种状态下，SDRAM芯片自己完成refresh的操作，不需要SDRAM controller的干涉（Auto refresh需要）。既然有刷新，SDRAM中的数据是自然可以保持住的。SDRAM进入self refresh后，SDRAM controller也会disable输出到SDRAM的clock，从而整体的功耗都降低下来。

对于软件工程师，除了timing的设定，SDRAM芯片已经SDRAM controller的电源管理相关的控制也是主要内容，这部分的内容和具体的SDRAM controller相关，不过掌握了上述内容之后，应该很容易进行配置，这里就不再具体描述了。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/basic_tech/sdram-internals.html)。

---
title: "vim使用技巧摘录"
date: 2014-06-10T16:16:12+08:00
url: "/linux_application/vim_skill.html"
gid: "50"
emlog_type: "blog"
summary: "平时读代码、写程序都是在vim（Vi Improved）下进行，总结了一些自己比较喜欢的技巧，贴出来和大家分享一下。 注：这些技巧只是蜗蜗比较喜欢，写在这里的主要目的是备份（以后换系统了，直接贴进去就可以了）。而每个人的习惯都不一样，因此仅供大家参考。"
author: "wowo"
category: "Linux应用技巧"
category_alias: "linux_application"
tags: ["vim", "vim_rc"]
views: 18859
comment_count: 3
aliases:
  - "/linux_application/50.html"
  - "/50.html"
---

平时读代码、写程序都是在vim（Vi Improved）下进行，总结了一些自己比较喜欢的技巧，贴出来和大家分享一下。

注：这些技巧只是蜗蜗比较喜欢，写在这里的主要目的是备份（以后换系统了，直接贴进去就可以了）。而每个人的习惯都不一样，因此仅供大家参考。

1. 创建vim的配置文件（.vimrc）

> vim ~/.vimrc

2. 在.vimrc中，根据自己的习惯，添加控制指令，使vim更高效（对自己而言）  

> "Highlight all search pattern matches   
> set hls  
> "Map F12 to create ctags index in current directory   
> map <F12> :!ctags -R <CR><CR>  
> "A shotcut to execute the grep command   
> map mg :!grep <C-R><C-W> . -r <CR>  
> "change the comment color 
>
> hi Comment ctermfg=6

3. 解释如下  

- set hls，看代码时，使用‘/’或者‘#’搜索指定的关键字时，高亮得到的所有结果
- map <F12> :!ctags -R <CR><CR> ，重映射F12键，这样可以一键在当前目录下创建ctags的索引
- map mg :!grep <C-R><C-W> . -r <CR>，一个执行grep命令的快捷方式。编写、查看代码时，敲击’mg’两个字母，即可直接grep光标所在位置的单词
- hi Comment ctermfg=6，看代码时，默认的注释颜色为深蓝色，看着太吃力了，改为浅蓝色，就好看多了

4. 其它技巧

- 阅读代码时，如果使用ctags命令创建了索引，将光标移至指定的函数上，CTRL+]会跳转到第一个匹配的定义处，g]会列出所有匹配的定义，CTRL+t返回上一个界面
- ‘shift + k’，vim内置的按键映射（:! man xxx），用于调用man命令，查看光标所在位置的帮助文档

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/linux_application/vim_skill.html)。*

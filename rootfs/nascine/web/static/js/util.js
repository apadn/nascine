
// 进度条配置
NProgress.configure({ showSpinner: false });

// Ajax主方法
function ajax_post(cmd, params, handler, aync=true, show_progress=true) {
    if (show_progress) {
        NProgress.start();
    }
    let data = {
        cmd: cmd,
        data: JSON.stringify(params)
    };
    $.ajax({
        type: "POST",
        url: "do?random=" + Math.random(),
        dataType: "json",
        data: data,
        cache: false,
        async: aync,
        timeout: 0,
        success: function (data) {
            if (show_progress) {
                NProgress.done();
            }
            if (handler) {
                handler(data);
            }
        },
        error: function (xhr, textStatus, errorThrown) {
            if (show_progress) {
                NProgress.done();
            }
            if (xhr && xhr.status === 200) {
                handler({code: 0});
            } else {
                handler({code: -99, msg: "网络错误"});
            }
        }
    });
}

// 备份文件下载
function ajax_backup(handler) {
    const downloadURL = "/backup";
    let xhr = new XMLHttpRequest()
    xhr.open('POST', downloadURL, true);
    xhr.responseType = 'arraybuffer';
    xhr.onload = function () {
        if (this.status === 200) {
            let type = xhr.getResponseHeader('Content-Type')
            let fileName = xhr.getResponseHeader('Content-Disposition')
                .split(';')[1]
                .split('=')[1]
                .replace(/\"/g, '')

            let blob = new Blob([this.response], {type: type})
            if (typeof window.navigator.msSaveBlob !== 'undefined') {
                /*
                 * IE workaround for "HTML7007: One or more blob URLs were revoked by closing
                 * the blob for which they were created. These URLs will no longer resolve as
                 * the data backing the URL has been freed."
                 */
                window.navigator.msSaveBlob(blob, fileName);
            } else {
                let URL = window.URL || window.webkitURL;
                let objectUrl = URL.createObjectURL(blob);
                console.log(objectUrl);
                if (fileName) {
                    const a = document.createElement('a');
                    // safari doesn't support this yet
                    if (typeof a.download === 'undefined') {
                        window.location = objectUrl
                    } else {
                        a.href = objectUrl;
                        a.download = fileName;
                        document.body.appendChild(a);
                        a.click();
                        a.remove();
                    }
                } else {
                    window.location = objectUrl;
                }
            }
        }
        if (handler) {
            handler();
        }
    };
    xhr.send();
}

// 获取链接参数
function getQueryVariable(variable) {
    const query = window.location.search.substring(1);
    const vars = query.split("&");
    for (let i = 0; i < vars.length; i++) {
        const pair = vars[i].split("=");
        if (pair[0] == variable) {
            return pair[1];
        }
    }
    return false;
}

// 鼠标提示等待
function make_cursor_busy() {
    const body = document.querySelector("body");
    body.style.cursor = "wait";
}

// 鼠标取消等待
function cancel_cursor_busy() {
    const body = document.querySelector("body");
    body.style.cursor = "default";
}

// 是否触摸屏设备
function is_touch_device() {
    return 'ontouchstart' in window;
}

// replaceAll浏览器兼容
String.prototype.replaceAll = function (s1, s2) {
    return this.replace(new RegExp(s1, "gm"), s2)
}

function select_name(name) {
    if (name.startsWith("\^")) {
        return `name^=${name.substring(1)}`;
    } else {
        return `name=${name}`;
    }
}

/**
 * 全选按钮绑定
 * @param: btnobj 按钮对象
 * @param: name 被管理checkbox的name
 **/
function select_btn_SelectALL(btnobj, name) {
    if ($(btnobj).text() === "全选") {
        $(`input[${select_name(name)}][type=checkbox]`).prop("checked", true);
        $(btnobj).text("全不选");
    } else {
        $(`input[${select_name(name)}][type=checkbox]`).prop("checked", false);
        $(btnobj).text("全选");
    }
}

/**
 * 全选事件
 * @param: status 全选框状态
 * @param: name 被管理checkbox的name
 **/
function select_SelectALL(status, name) {
    $(`input[${select_name(name)}][type=checkbox]`).prop("checked", status);
}

/**
 * 部分选定事件
 * @param: status 全选框状态
 * @param: name 被管理checkbox的name
 **/
function select_SelectPart(condition, name) {
    $(`input[${select_name(name)}][type=checkbox]`).each(function () {
        if (condition && condition.includes($(this).val())) {
            $(this).prop("checked", true);
        } else {
            $(this).prop("checked", false);
        }
    });
}

/**
 * 获取选中input元素value
 * @param: name 被管理checkbox的name
 **/
function select_GetSelectedVAL(name) {
    let selectedVAL = [];
    $(`input[${select_name(name)}][type=checkbox]`).each(function () {
        if ($(this).prop("checked")) {
        selectedVAL.push($(this).val());
        }
    });
    return selectedVAL;
}

/**
 * 获取隐藏input元素value
 * @param: name 被管理checkbox的name
 **/
function select_GetHiddenVAL(name) {
    let hiddenVAL = [];
    $(`input[${select_name(name)}][type=hidden]`).each(function () {
        hiddenVAL.push($(this).val());
    });
    return hiddenVAL;
}

/**
 * 获取元素下input设置
 * @param: id 元素id
 **/
function input_select_GetVal(id, prefix=null) {
    let params = {};
    $(`#${id} input`).each(function () {
        let key = $(this).attr("id");
        if (key) {
            params[(prefix) ? key.replace(prefix, "") : key] = ($(this).attr("type") === "checkbox") ? !!$(this).prop("checked") : $(this).val();
        }
    });
    $(`#${id} select`).each(function () {
        let key = $(this).attr("id");
        if (key) {
            params[(prefix) ? key.replace(prefix, "") : key] = $(this).val();
        }
    });
    return params;
}

/**
 * 对象数组排序，针对纯英文、数字或纯中文的排序
 * @param: objArr 需要排序的对象数组
 * @param: sortKey  需要进行排序的键
 * @param: sortType asc升序(默认)  desc 降序
 **/
function dictArraySorting(objArr,sortKey,sortType="asc") {
    return objArr.sort(function (obj1, obj2) {
        let val1 = obj1[sortKey];
        let val2 = obj2[sortKey];
        if (!isNaN(Number(val1)) && !isNaN(Number(val2))) {
            val1 = Number(val1);
            val2 = Number(val2);
        }
        if (sortType === "asc") {
            return val1 - val2;
        } else if (sortType === "desc") {
            return val2 - val1;
        }
    })
}

/**
 * bytes转换为size
 * @param: bytes 字节数
 **/
function bytesToSize(bytes) {
    let size = ''
    if (bytes < 0.1 * 1024) { // 小于0.1KB 则转化成B
        size = bytes + ' B'
    }
    else if (bytes < 0.1 * 1024 * 1024) { // 小于0.1MB 则转换成KB
        size = (bytes / 1024).toFixed(2) + ' KB'
    }
    else if (bytes < 0.1 * 1024 * 1024 * 1024) { // 小于0.1GB 则转换成MB
        size = (bytes / (1024 * 1024)).toFixed(2) + ' MB'
    }
    else if (bytes < 0.1 * 1024 * 1024 * 1024 * 1024) { // 小于0.1TB 则转换成GB
        size = (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
    }
    else if (bytes < 0.1 * 1024 * 1024 * 1024 * 1024 * 1024) { // 小于0.1PB 则转换成TB
        size = (bytes / (1024 * 1024 * 1024 * 1024)).toFixed(2) + ' TB'
    }
    else if (bytes < 0.1 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024) { // 小于0.1EB 则转换成PB
        size = (bytes / (1024 * 1024 * 1024 * 1024 * 1024)).toFixed(2) + ' PB'
    }
    return size
}

/**
 * 暂停
 * @param: ms 暂停毫秒数
 **/
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * 比较版本号大小，v1大于v2时返回1，相等返回0，v1小于v2返回-1；
 * 主版本一致但 commit 不同时返回2（同版本不同提交）。
 * 支持 v2.9.1、v2.9.10、v2.9.1-r2、2.9.1-apple.1 等写法（末尾修订号参与比较）。
 */
function compareVersion(version1, version2) {
    function parse(v) {
        const str = (v || '').trim();
        const parts = str.split(/\s+/);
        const main = parts[0] || '';
        const commit = parts[1] || '';
        const matched = main.replace(/^v/i, '').match(/^(\d+(?:\.\d+)*)(?:[-_.]?[A-Za-z]+[._-]?(\d+)?)?$/);
        let nums;
        let revision = 0;
        if (matched) {
            nums = matched[1].split('.').map(n => parseInt(n, 10) || 0);
            revision = matched[2] ? parseInt(matched[2], 10) : 0;
        } else {
            nums = main.replace(/^v/i, '').split('.').map(n => parseInt(n, 10) || 0);
        }
        return { nums: nums, revision: revision, commit: commit };
    }

    const a = parse(version1);
    const b = parse(version2);
    const len = Math.max(a.nums.length, b.nums.length);
    for (let i = 0; i < len; i++) {
        const n1 = a.nums[i] || 0;
        const n2 = b.nums[i] || 0;
        if (n1 > n2) {
            return 1;
        } else if (n1 < n2) {
            return -1;
        }
    }

    if (a.revision > b.revision) {
        return 1;
    } else if (a.revision < b.revision) {
        return -1;
    }

    if (a.commit && b.commit && a.commit !== b.commit) {
        return 2;
    }
    return 0;
}


// 计算滚动条相对于页面底部的距离比例
function getScrollRate(){
    const winH = window.innerHeight; //页面可视区域高度
    const pageH = $("#page_content").height(); //页面总高度
    const scrollT = document.body.scrollTop || window.pageYOffset; //滚动条top
    return (pageH - winH - scrollT) / winH;
}

// 判断元素出现滚动条
function hasScrollbar() {
    // 判断是否大于2是因为我观察到部分情况下body可滚动的高度会比可视区域大1
    return (document.body.scrollHeight - (window.innerHeight || document.documentElement.clientHeight)) > 2;
}

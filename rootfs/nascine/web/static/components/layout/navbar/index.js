import { LayoutNavbarButton } from "./button.js"; export { LayoutNavbarButton };
import { html, nothing } from "../../utility/lit-core.min.js";
import { CustomElement } from "../../utility/utility.js";

// name: 服务原名
// page: 导航路径
// icon: 项目图标
// : 显示别名 (可选)
const navbar_list = [
  {
    name: "我的媒体库",
    page: "index",
    icon: html`
      <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-home" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"></path><polyline points="5 12 3 12 12 3 21 12 19 12"></polyline><path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2v-7"></path><path d="M9 21v-6a2 2 0 0 1 2 -2h2a2 2 0 0 1 2 2v6"></path></svg>
    `,
  },
  {
    name: "下载管理",
    list: [
      {
        name: "正在下载",
        page: "downloading",
        icon: html`
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/loader.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-loader" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M12 6l0 -3"></path>
            <path d="M16.25 7.75l2.15 -2.15"></path>
            <path d="M18 12l3 0"></path>
            <path d="M16.25 16.25l2.15 2.15"></path>
            <path d="M12 18l0 3"></path>
            <path d="M7.75 16.25l-2.15 2.15"></path>
            <path d="M6 12l-3 0"></path>
            <path d="M7.75 7.75l-2.15 -2.15"></path>
          </svg>
        `,
      },
      {
        name: "近期下载",
        page: "downloaded",
        icon: html`
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-download" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"></path><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2 -2v-2"></path><polyline points="7 11 12 16 17 11"></polyline><line x1="12" y1="4" x2="12" y2="16"></line></svg>
        `,
      },
    ],
  },
  {
    name: "服务",
    page: "service",
    icon: html`
      <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-layout-2" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"></path><rect x="4" y="4" width="6" height="5" rx="2"></rect><rect x="4" y="13" width="6" height="7" rx="2"></rect><rect x="14" y="4" width="6" height="7" rx="2"></rect><rect x="14" y="15" width="6" height="5" rx="2"></rect></svg>
    `,
  },
  {
    name: "系统设置",
    also: "设置",
    list: [
      {
        name: "基础设置",
        page: "basic",
        icon: html`
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-settings" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"></path><path d="M10.325 4.317c.426 -1.756 2.924 -1.756 3.35 0a1.724 1.724 0 0 0 2.573 1.066c1.543 -.94 3.31 .826 2.37 2.37a1.724 1.724 0 0 0 1.065 2.572c1.756 .426 1.756 2.924 0 3.35a1.724 1.724 0 0 0 -1.066 2.573c.94 1.543 -.826 3.31 -2.37 2.37a1.724 1.724 0 0 0 -2.572 1.065c-.426 1.756 -2.924 1.756 -3.35 0a1.724 1.724 0 0 0 -2.573 -1.066c-1.543 .94 -3.31 -.826 -2.37 -2.37a1.724 1.724 0 0 0 -1.065 -2.572c-1.756 -.426 -1.756 -2.924 0 -3.35a1.724 1.724 0 0 0 1.066 -2.573c-.94 -1.543 .826 -3.31 2.37 -2.37c1 .608 2.296 .07 2.572 -1.065z"></path><circle cx="12" cy="12" r="3"></circle></svg>
        `,
      },
      {
        name: "用户管理",
        page: "users",
        icon: html`
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/users.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-users" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M9 7m-4 0a4 4 0 1 0 8 0a4 4 0 1 0 -8 0"></path>
            <path d="M3 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2"></path>
            <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
            <path d="M21 21v-2a4 4 0 0 0 -3 -3.85"></path>
          </svg>
        `,
      },
      {
        name: "媒体库",
        page: "library",
        icon: html`
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/stereo-glasses.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-stereo-glasses" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M8 3h-2l-3 9"></path>
            <path d="M16 3h2l3 9"></path>
            <path d="M3 12v7a1 1 0 0 0 1 1h4.586a1 1 0 0 0 .707 -.293l2 -2a1 1 0 0 1 1.414 0l2 2a1 1 0 0 0 .707 .293h4.586a1 1 0 0 0 1 -1v-7h-18z"></path>
            <path d="M7 16h1"></path>
            <path d="M16 16h1"></path>
          </svg>
        `,
      },
      {
        name: "目录同步",
        page: "directorysync",
        icon: html`
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/refresh.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-refresh" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4"></path>
            <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4"></path>
          </svg>
        `,
      },
      {
        name: "消息通知",
        page: "notification",
        icon: html`
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/bell.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-bell" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M10 5a2 2 0 0 1 4 0a7 7 0 0 1 4 6v3a4 4 0 0 0 2 3h-16a4 4 0 0 0 2 -3v-3a7 7 0 0 1 4 -6"></path>
            <path d="M9 17v1a3 3 0 0 0 6 0v-1"></path>
          </svg>
        `,
      },
      {
        name: "过滤规则",
        page: "filterrule",
        icon: html`
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/filter.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-filter" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M5.5 5h13a1 1 0 0 1 .5 1.5l-5 5.5l0 7l-4 -3l0 -4l-5 -5.5a1 1 0 0 1 .5 -1.5"></path>
          </svg>
        `,
      },
      {
        name: "自定义识别词",
        page: "customwords",
        icon: html`
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/a-b.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-a-b" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M3 16v-5.5a2.5 2.5 0 0 1 5 0v5.5m0 -4h-5"></path>
            <path d="M12 6l0 12"></path>
            <path d="M16 16v-8h3a2 2 0 0 1 0 4h-3m3 0a2 2 0 0 1 0 4h-3"></path>
          </svg>
        `,
      },
      {
        name: "下载器",
        page: "downloader",
        icon: html`
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/download.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-download" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2 -2v-2"></path>
            <path d="M7 11l5 5l5 -5"></path>
            <path d="M12 4l0 12"></path>
          </svg>
        `,
      },
      {
        name: "媒体服务器",
        page: "mediaserver",
        icon: html`
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/server-cog.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-server-cog" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M3 4m0 3a3 3 0 0 1 3 -3h12a3 3 0 0 1 3 3v2a3 3 0 0 1 -3 3h-12a3 3 0 0 1 -3 -3z"></path>
            <path d="M12 20h-6a3 3 0 0 1 -3 -3v-2a3 3 0 0 1 3 -3h10.5"></path>
            <path d="M18 18m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"></path>
            <path d="M18 14.5v1.5"></path>
            <path d="M18 20v1.5"></path>
            <path d="M21.032 16.25l-1.299 .75"></path>
            <path d="M16.27 19l-1.3 .75"></path>
            <path d="M14.97 16.25l1.3 .75"></path>
            <path d="M19.733 19l1.3 .75"></path>
            <path d="M7 8v.01"></path>
            <path d="M7 16v.01"></path>
          </svg>
        `,
      },
      {
        name: "字幕",
        page: "subtitle",
        icon: html`
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/badge-cc.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-badge-cc" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M3 5m0 2a2 2 0 0 1 2 -2h14a2 2 0 0 1 2 2v10a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2z"></path>
            <path d="M10 10.5a1.5 1.5 0 0 0 -3 0v3a1.5 1.5 0 0 0 3 0"></path>
            <path d="M17 10.5a1.5 1.5 0 0 0 -3 0v3a1.5 1.5 0 0 0 3 0"></path>
          </svg>
        `,
      },
    ],
  },
];

export class LayoutNavbar extends CustomElement {
  static properties = {
    layout_gopage: { attribute: "layout-gopage" },
    layout_appversion: { attribute: "layout-appversion"},
    layout_updateurl: { attribute: "layout-updateurl"},
    layout_userpris: { attribute: "layout-userpris", type: Array },
    _active_name: { state: true},
    _update_appversion: { state: true },
    _update_url: { state: true },
    _is_update: { state: true },
  };

  constructor() {
    super();
    this.layout_gopage = "";
    this.layout_appversion = "v1.0.0";
    this.layout_updateurl = "";
    this.layout_userpris = navbar_list.map((item) => (item.name));
    this._active_name = "";
    this._update_appversion = "";
    this._update_url = "";
    this._is_update = false;
    this.classList.add("navbar","navbar-vertical","navbar-expand-lg","lit-navbar-fixed","lit-navbar","lit-navbar-hide-scrollbar");
  }

  firstUpdated() {
    // 版本徽标默认指向镜像仓库页面（更新方式为拉取镜像）
    if (!this._update_url && this.layout_updateurl) {
      this._update_url = this.layout_updateurl;
    }
    // 加载页面
    if (this.layout_gopage) {
      navmenu(this.layout_gopage);
    } else if (window.history.state?.page) {
      //console.log("刷新页面");
      window_history_refresh();
    } else {
      // 打开第一个有权限的页面（老配置里可能残留已下线的入口名）
      let opened = false;
      for (const item of navbar_list) {
        if (item.name === this.layout_userpris[0]) {
          navmenu(item.page ?? item.list[0].page);
          opened = true;
          break;
        }
      }
      if (!opened && navbar_list.length > 0) {
        navmenu(navbar_list[0].page ?? navbar_list[0].list[0].page);
      }
      // 默认展开下载管理
      setTimeout(() => { this.show_collapse("downloading") }, 200);
    }
    // 删除logo动画 加点延迟切换体验好
    setTimeout(() => {
      document.querySelector("#logo_animation").remove();
      this.removeAttribute("hidden");
      document.querySelector("#page_content").removeAttribute("hidden");
      document.querySelector("layout-searchbar").removeAttribute("hidden");
    }, 200);
    // 检查更新
    if (this.layout_userpris.includes("系统设置")) {
      this._check_new_version();
    }
  }

  _check_new_version() {
    ajax_post("version", {}, (ret) => {
      if (ret.code === 0) {
        let url = null;
        switch (compareVersion(ret.version, this.layout_appversion)) {
          case 1:
            url = ret.url;
            break;
          case 2:
            url = this.layout_updateurl;
            break;
        }
        if (url) {
          this._update_url = url;
          this._update_appversion = ret.version;
          this._is_update = true;
        }
      }
    });
  }

  update_active(page) {
    this._active_name = page ?? window.history.state?.page;
    this._sync_crumb(this._active_name);
    this.show_collapse(this._active_name);
  }

  // 顶栏面包屑：分组 › 页面，找不到就留空
  _sync_crumb(page) {
    const bar = document.querySelector("layout-searchbar");
    if (!bar || typeof bar.set_crumb !== "function") return;
    for (const item of navbar_list) {
      if (item.page === page) {
        bar.set_crumb("", item.also ?? item.name);
        return;
      }
      for (const child of item.list ?? []) {
        if (child.page === page) {
          bar.set_crumb(item.also ?? item.name, child.also ?? child.name);
          return;
        }
      }
    }
  }

  // 侧栏不再折叠，只把当前项滚进视野
  show_collapse(page) {
    const active = this.querySelector(".ap-item.is-active");
    if (active && active.scrollIntoView) {
      active.scrollIntoView({ block: "nearest" });
    }
  }

  render() {
    return html`
      <style>

        .navbar {
          min-height: 3rem !important;
        }

        .lit-navbar-fixed {
          position:fixed;
          top:0;
          left:0;
          z-index:1031
        }

        .lit-navbar-hide-scrollbar {
          overflow-y: scroll!important;
          overscroll-behavior-y: contain!important;
          scrollbar-width: none!important;
          -ms-overflow-style: none!important;
        }

        .lit-navbar-hide-scrollbar::-webkit-scrollbar {
          display: none;
        }

        .theme-light .lit-navbar,
        .theme-dark .lit-navbar {
          background-color: transparent;
        }

        /* lg 以下由 Bootstrap offcanvas 接管显示，不做高度裁剪，
           否则抽屉会被 max-height:0 截断，手机上打不开导航 */

      </style>
      <div class="container-fluid">
        <div class="offcanvas offcanvas-start d-flex lit-navbar-canvas" tabindex="-1" id="litLayoutNavbar">
          <div class="ap-side">
            <a class="ap-brand" href="javascript:void(0)" data-bs-dismiss="offcanvas"
               @click=${() => navmenu(navbar_list[0].page)}>
              <img src="../static/img/logo-mark.png" alt="nascine" class="ap-brand-mark">
              <span class="ap-brand-text">
                <span class="ap-brand-name">nascine</span>
                <span class="ap-brand-sub">影音库中枢</span>
              </span>
            </a>
            <nav class="ap-nav">
              ${navbar_list.map((item) => html`
                ${this.layout_userpris.includes(item.name)
                ? html`
                    ${item.list?.length > 0
                    ? html`
                        <div class="ap-group">
                          <div class="ap-group-label">${item.also ?? item.name}</div>
                          <div class="ap-items">
                            ${item.list.map((drop) => this._render_page_item(drop))}
                          </div>
                        </div>`
                    : html`
                        <div class="ap-group ap-group-single">
                          <div class="ap-items">${this._render_page_item(item)}</div>
                        </div>`}`
                : nothing}
              `)}
            </nav>
            <div class="ap-side-foot">
              <a class="ap-version ${this._is_update ? "is-new" : ""}" href=${this._update_url}
                 target="_blank" rel="noreferrer" title="检查更新">
                ${this._is_update ? html`<span class="ap-version-dot"></span>` : nothing}
                ${!this._is_update ? this.layout_appversion : html`<del>${this.layout_appversion}</del>`}
                ${this._is_update
                ? html`
                    <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-arrow-up-circle" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                      <circle cx="12" cy="12" r="9"></circle>
                      <polyline points="12 8 8 12 12 16"></polyline>
                      <line x1="16" y1="12" x2="8" y2="12" transform="rotate(90 12 12)"></line>
                    </svg>`
                : nothing}
              </a>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  _render_page_item(item) {
    return html`
      <a class="ap-item${this._active_name === item.page ? " is-active" : ""}"
         href="javascript:void(0)" data-bs-dismiss="offcanvas"
         data-lit-page=${item.page}
         @click=${() => { navmenu(item.page) }}>
        <span class="ap-item-icon">${item.icon ?? nothing}</span>
        <span class="ap-item-label">${item.also ?? item.name}</span>
      </a>`;
  }

}

window.customElements.define("layout-navbar", LayoutNavbar);
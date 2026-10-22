import { html, nothing } from "../../utility/lit-core.min.js";
import { CustomElement } from "../../utility/utility.js";

export class LayoutSearchbar extends CustomElement {
  static properties = {
    layout_systemflag: { attribute: "layout-systemflag" },
    layout_username: { attribute: "layout-username" },
    layout_userpris: { attribute: "layout-userpris", type: Array },
    _crumb_group: { state: true },
    _crumb_page: { state: true },
  };

  constructor() {
    super();
    this.layout_systemflag = "Docker";
    this.layout_username = "admin";
    this.layout_userpris = ["系统设置"];
    this._crumb_group = "";
    this._crumb_page = "";
    this.classList.add("navbar", "fixed-top", "lit-searchbar");
  }

  firstUpdated() {
    // 当前状态：是否模糊
    let blur = false;
    window.addEventListener("scroll", () => {
      const scroll_length = document.body.scrollTop || window.pageYOffset;
      if (!blur && scroll_length >= 5) {
        blur = true;
        this.classList.add("lit-searchbar-blur");
      } else if (blur && scroll_length < 5) {
        blur = false;
        this.classList.remove("lit-searchbar-blur");
      }
    });
  }

  // 由 layout-navbar 调用：更新顶栏面包屑
  set_crumb(group, page) {
    this._crumb_group = group || "";
    this._crumb_page = page || "";
  }

  disconnectedCallback() {
    super.disconnectedCallback();
  }

  get input() {
    return this.querySelector(".home_search_bar") ?? null;
  }

  render() {
    return html`
      <style>

        .lit-searchbar {
          background-color: var(--ap-chrome, rgba(255, 255, 255, 0.72)) !important;
          border-right: none !important;
          border-bottom: 1px solid var(--ap-separator, rgba(60, 60, 67, 0.1)) !important;
          box-shadow: none !important;
          -webkit-backdrop-filter: saturate(180%) blur(28px);
          backdrop-filter: saturate(180%) blur(28px);
        }

        .lit-searchbar-blur {
          background-color: var(--ap-chrome, rgba(255, 255, 255, 0.85)) !important;
        }

      </style>
      <div class="container-fluid nav-search-bar">
        <div class="ap-topbar">
          <layout-navbar-button></layout-navbar-button>
          <div class="ap-crumb">
            ${this._crumb_group && this._crumb_group !== this._crumb_page
              ? html`
                  <span class="ap-crumb-group">${this._crumb_group}</span>
                  <span class="ap-crumb-sep">/</span>`
              : nothing}
            <span class="ap-crumb-page">${this._crumb_page}</span>
          </div>
          <div class="ap-topbar-right">
            <div class="nav-item dropdown">
              <a href="#" class="nav-link ap-avatar d-flex lh-1 text-reset p-0" data-bs-toggle="dropdown"
                 aria-label="用户菜单">
                <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-user"
                    width="24" height="24" viewBox="0 0 24 24"
                    stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                  <circle cx="12" cy="7" r="4"></circle>
                  <path d="M6 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2"></path>
                </svg>
              </a>
              <div class="dropdown-menu dropdown-menu-end">
                <a class="dropdown-item hide-theme-dark" href="?theme=dark" role="button">暗黑风格</a>
                <a class="dropdown-item hide-theme-light" href="?theme=light" role="button">明亮风格</a>
                <div class="dropdown-divider"></div>
                ${this.layout_userpris.includes("系统设置")
                ? html`
                    <a class="dropdown-item" data-bs-toggle="offcanvas" href="#offcanvasEnd" role="button"
                      aria-controls="offcanvasEnd">消息中心</a>
                    <a class="dropdown-item" href="javascript:show_logging_modal()" role="button">实时日志</a>
                    <div class="dropdown-divider"></div>
                    ${["Docker", "Synology"].includes(this.layout_systemflag)
                    ? html`
                      <a href="javascript:restart()" class="dropdown-item">重启</a>
                      <a href="javascript:update()" class="dropdown-item">更新</a>`
                    : nothing }
                  `
                : nothing }
                <a href="javascript:logout()" class="dropdown-item">
                  注销 <span class="text-muted ms-2">${this.layout_username}</span>
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

}


window.customElements.define("layout-searchbar", LayoutSearchbar);

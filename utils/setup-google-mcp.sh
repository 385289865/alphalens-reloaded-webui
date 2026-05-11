#!/usr/bin/env bash
# ============================================================
# Google MCP (Chrome DevTools MCP) 管理工具
# Linux 无头环境 Chrome MCP 一键安装/卸载/检测
# ============================================================
# 使用方式:
#   bash setup-google-mcp.sh          交互式菜单
#   bash setup-google-mcp.sh --install   直接安装
#   bash setup-google-mcp.sh --uninstall 直接卸载
#   bash setup-google-mcp.sh --detect    直接检测
#   bash setup-google-mcp.sh --help      帮助信息
# ============================================================

SCRIPT_VERSION="1.0.0"
CHROME_DEBUG_PORT=${CHROME_DEBUG_PORT:-9222}

# ── ANSI 颜色 ──────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
REVERSE='\033[7m'
NC='\033[0m'

# ── 全局状态 ──────────────────────────────────────────────
DISTRO=""
DISTRO_VERSION=""
DISTRO_ID=""
PKG_MANAGER=""
PKG_INSTALL=""
PKG_QUERY=""
IS_WSL=false
IS_CONTAINER=false
IS_HEADLESS=true
ARCH=""

CHROME_BIN=""
CHROME_VERSION=""
NODE_BIN=""
NODE_VERSION=""
NPX_BIN=""
NVM_DIR="${NVM_DIR:-$HOME/.nvm}"

GLOBAL_MCP_JSON="${HOME}/.claude/mcp.json"
GLOBAL_SCRIPTS_DIR="${HOME}/.claude/scripts"

# 状态缓存（detect 填充）
STATUS_CHROME=""
STATUS_NODE=""
STATUS_NPX=""
STATUS_CHROME_VER=""
STATUS_NODE_VER=""
STATUS_NPX_VER=""
STATUS_MCP_CONFIG=""
STATUS_MCP_RUNNING=""

# ── 日志函数 ──────────────────────────────────────────────
log_info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[✓]${NC} $*"; }
log_warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
log_error()   { echo -e "${RED}[✗]${NC} $*"; }
log_step()    { echo -e "\n${CYAN}═══════════════════════════════════════${NC}"; echo -e "${BOLD}  第 $1 步: $2${NC}"; echo -e "${CYAN}═══════════════════════════════════════${NC}"; }
log_title()   { echo -e "\n${CYAN}╔════════════════════════════════════════════════╗${NC}"; echo -e "${CYAN}║${NC}  $1"; echo -e "${CYAN}╚════════════════════════════════════════════════╝${NC}"; }

# ── 工具函数 ──────────────────────────────────────────────
has_command() { command -v "$1" &>/dev/null; }

confirm() {
    # 用法: confirm "提示信息" [默认值]
    # 返回: 0=yes, 1=no
    local prompt="$1"
    local default="${2:-N}"
    local yn
    if [[ "$default" =~ ^[Yy] ]]; then
        prompt="$prompt [Y/n] "
    else
        prompt="$prompt [y/N] "
    fi
    read -r -p "$prompt" yn
    yn="${yn:-$default}"
    [[ "$yn" =~ ^[Yy] ]] && return 0 || return 1
}

# ── 步骤执行器（非 -e 下安全执行） ────────────────────────
run_step() {
    local name="$1"
    shift
    log_step "$name" "$*"
    if "$@"; then
        log_success "$name 完成"
        return 0
    else
        log_error "$name 失败"
        return 1
    fi
}

# ============================================================
# 1. 环境检测
# ============================================================

detect_system() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        DISTRO_ID="${ID}"
        DISTRO_VERSION="${VERSION_ID}"
        DISTRO="${ID} ${VERSION_ID}"
    elif [[ -f /etc/redhat-release ]]; then
        DISTRO_ID="rhel"
        DISTRO="$(cat /etc/redhat-release)"
    else
        DISTRO_ID="unknown"
        DISTRO="unknown"
    fi

    case "$DISTRO_ID" in
        debian|ubuntu)
            PKG_MANAGER="apt"
            PKG_QUERY="dpkg -l"
            PKG_INSTALL="apt-get install -y"
            ;;
        rhel|centos|almalinux|rocky)
            PKG_MANAGER="dnf"
            PKG_QUERY="rpm -q"
            PKG_INSTALL="dnf install -y"
            # 检查是否需要回退到 yum
            has_command dnf || { PKG_MANAGER="yum"; PKG_INSTALL="yum install -y"; }
            ;;
        fedora)
            PKG_MANAGER="dnf"
            PKG_QUERY="rpm -q"
            PKG_INSTALL="dnf install -y"
            ;;
        alpine)
            PKG_MANAGER="apk"
            PKG_QUERY="apk info -e"
            PKG_INSTALL="apk add"
            ;;
        arch)
            PKG_MANAGER="pacman"
            PKG_QUERY="pacman -Qi"
            PKG_INSTALL="pacman -S --noconfirm"
            ;;
        *)
            PKG_MANAGER=""
            PKG_INSTALL=""
            PKG_QUERY=""
            ;;
    esac

    ARCH="$(uname -m)"
}

detect_env() {
    # WSL
    if grep -qi microsoft /proc/version 2>/dev/null || grep -qi wsl /proc/version 2>/dev/null; then
        IS_WSL=true
    fi
    # 容器
    if [[ -f /.dockerenv ]] || grep -q docker /proc/1/cgroup 2>/dev/null; then
        IS_CONTAINER=true
    fi
    # 无头
    if [[ -n "${DISPLAY:-}" || -n "${WAYLAND_DISPLAY:-}" ]]; then
        IS_HEADLESS=false
    fi
}

detect_chrome() {
    CHROME_BIN=""
    CHROME_VERSION=""
    local candidates=("google-chrome" "google-chrome-stable" "chromium-browser" "chromium" "chromium-browser-bin" "google-chrome-beta" "google-chrome-unstable")
    for bin in "${candidates[@]}"; do
        if has_command "$bin"; then
            CHROME_BIN="$bin"
            CHROME_VERSION="$($bin --version 2>/dev/null | head -1)"
            CHROME_VERSION="${CHROME_VERSION:-unknown}"
            return 0
        fi
    done
    # 额外检查常见路径
    local paths=("/usr/bin/chromium" "/usr/bin/chromium-browser" "/snap/bin/chromium" "/opt/google/chrome/chrome" "/usr/bin/google-chrome")
    for p in "${paths[@]}"; do
        if [[ -x "$p" ]]; then
            CHROME_BIN="$p"
            CHROME_VERSION="$($p --version 2>/dev/null | head -1)"
            CHROME_VERSION="${CHROME_VERSION:-unknown}"
            return 0
        fi
    done
    return 1
}

detect_nodejs() {
    NODE_BIN=""
    NODE_VERSION=""
    NPX_BIN=""

    # 优先 nvm
    if [[ -s "$NVM_DIR/nvm.sh" ]]; then
        # shellcheck source=/dev/null
        . "$NVM_DIR/nvm.sh"
        local nvm_node
        nvm_node="$(command -v node 2>/dev/null || true)"
        if [[ -n "$nvm_node" ]]; then
            NODE_BIN="$nvm_node"
            NODE_VERSION="$("$nvm_node" --version 2>/dev/null)"
            NPX_BIN="$(command -v npx 2>/dev/null || true)"
            return 0
        fi
    fi

    # 系统 node
    if has_command node; then
        NODE_BIN="$(command -v node)"
        NODE_VERSION="$("$NODE_BIN" --version 2>/dev/null)"
        NPX_BIN="$(command -v npx 2>/dev/null || true)"
        return 0
    fi

    return 1
}

detect_mcp_config() {
    STATUS_MCP_CONFIG=""
    STATUS_MCP_RUNNING=""

    # 检查全局 mcp.json
    if [[ -f "$GLOBAL_MCP_JSON" ]]; then
        if python3 -c '
import json, sys
try:
    with open(sys.argv[1]) as f:
        d = json.load(f)
    if "chrome-devtools" in d.get("mcpServers", {}):
        sys.exit(0)
    sys.exit(1)
except Exception:
    sys.exit(1)
' "$GLOBAL_MCP_JSON" 2>/dev/null; then
            STATUS_MCP_CONFIG="已配置"
        else
            STATUS_MCP_CONFIG="未配置"
        fi
    else
        STATUS_MCP_CONFIG="未配置"
    fi

    # 检查 DevTools 是否运行
    if curl -sf "http://127.0.0.1:${CHROME_DEBUG_PORT}/json/version" >/dev/null 2>&1; then
        STATUS_MCP_RUNNING="运行中"
    else
        STATUS_MCP_RUNNING="未运行"
    fi
}

detect_all() {
    detect_system
    detect_env
    detect_chrome || true
    detect_nodejs || true
    detect_mcp_config

    # 填充状态
    STATUS_CHROME="${CHROME_BIN:+已安装}"
    STATUS_CHROME="${STATUS_CHROME:-未安装}"
    STATUS_CHROME_VER="${CHROME_VERSION:-}"

    STATUS_NODE="${NODE_BIN:+已安装}"
    STATUS_NODE="${STATUS_NODE:-未安装}"
    STATUS_NODE_VER="${NODE_VERSION:-}"

    if [[ -n "$NPX_BIN" ]]; then
        STATUS_NPX="已安装"
        STATUS_NPX_VER="$("$NPX_BIN" --version 2>/dev/null || echo "")"
    else
        STATUS_NPX="未安装"
        STATUS_NPX_VER=""
    fi
}

# ============================================================
# 2. TUI 菜单
# ============================================================

# 终端设置保存/恢复
term_cleanup() {
    stty echo icanon 2>/dev/null || true
}
trap term_cleanup EXIT INT TERM

render_menu() {
    local -n items=$1
    local selected=$2
    local status_line=$3

    clear
    echo -e "${CYAN}╔═══════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}Google MCP 管理工具 v${SCRIPT_VERSION}${NC}            ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  Chrome DevTools MCP · Linux 无头环境     ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${YELLOW}使用 ↑ ↓ 键移动光标，Enter 确认${NC}"
    echo ""

    for i in "${!items[@]}"; do
        if [[ $i -eq $selected ]]; then
            echo -e "  ${GREEN}${REVERSE} → ${items[$i]} ${NC}"
        else
            echo -e "    ${items[$i]}"
        fi
    done

    echo ""
    echo -e "  ${BLUE}当前状态:${NC} ${status_line}"
    echo ""
}

detect_status_line() {
    local parts=()
    [[ "$STATUS_CHROME" == "已安装" ]] && parts+=("Chromium ${GREEN}✓${NC}") || parts+=("Chromium ${RED}✗${NC}")
    [[ "$STATUS_NODE" == "已安装" ]] && parts+=("Node.js ${GREEN}✓${NC}") || parts+=("Node.js ${RED}✗${NC}")
    [[ "$STATUS_MCP_CONFIG" == "已配置" ]] && parts+=("MCP ${GREEN}✓${NC}") || parts+=("MCP ${RED}✗${NC}")
    local IFS=" "
    echo -e "${parts[*]}"
}

show_menu() {
    local menu_items=("📦 安装 Google MCP" "🗑 卸载 Google MCP" "🔍 检测当前环境" "❌ 退出")
    local selected=0
    local key

    # 预先检测
    detect_all

    while true; do
        local status
        status="$(detect_status_line)"
        render_menu menu_items "$selected" "$status"

        # 读取键盘
        read -rsn1 key
        if [[ $key == $'\e' ]]; then
            read -rsn2 -t 0.05 key2
            case "$key2" in
                '[A') ((selected--)); [[ $selected -lt 0 ]] && selected=$((${#menu_items[@]} - 1)) ;;
                '[B') ((selected++)); [[ $selected -ge ${#menu_items[@]} ]] && selected=0 ;;
            esac
        elif [[ -z $key || $key == $'\n' ]]; then
            case $selected in
                0) install_all;;
                1) uninstall_all;;
                2) detect_all; show_report;;
                3) clear; echo "再见！"; exit 0;;
            esac
            # 操作完成后暂停
            if [[ $selected -lt 3 ]]; then
                echo ""
                read -r -p "按 Enter 返回主菜单..."
            fi
        fi
    done
}

# ============================================================
# 3. 检测报告
# ============================================================

show_report() {
    clear
    log_title "🔍 环境检测报告"

    echo -e "${BOLD}系统信息${NC}"
    echo "  发行版:    ${DISTRO:-未知}"
    echo "  架构:      ${ARCH}"
    echo "  运行环境:  $([ "$IS_CONTAINER" = true ] && echo "容器" || echo "宿主") | $([ "$IS_WSL" = true ] && echo "WSL" || echo "原生")"
    echo "  显示模式:  $([ "$IS_HEADLESS" = true ] && echo "无头 (HEADLESS)" || echo "有桌面")"
    echo ""

    echo -e "${BOLD}组件状态${NC}"
    printf "  %-20s %-12s %s\n" "组件" "状态" "版本"
    echo "  ───────────────────────────────────────────"
    printf "  %-20s %b %s\n" "Chromium" "$([ "$STATUS_CHROME" == "已安装" ] && echo "${GREEN}已安装${NC}" || echo "${RED}未安装${NC}")" "$STATUS_CHROME_VER"
    printf "  %-20s %b %s\n" "Node.js" "$([ "$STATUS_NODE" == "已安装" ] && echo "${GREEN}已安装${NC}" || echo "${RED}未安装${NC}")" "$STATUS_NODE_VER"
    printf "  %-20s %b %s\n" "npm/npx" "$([ "$STATUS_NPX" == "已安装" ] && echo "${GREEN}已安装${NC}" || echo "${RED}未安装${NC}")" "$STATUS_NPX_VER"
    printf "  %-20s %b\n" "MCP 配置" "$([ "$STATUS_MCP_CONFIG" == "已配置" ] && echo "${GREEN}已配置${NC}" || echo "${RED}未配置${NC}")"
    printf "  %-20s %b\n" "DevTools 端口" "$([ "$STATUS_MCP_RUNNING" == "运行中" ] && echo "${GREEN}${STATUS_MCP_RUNNING}${NC}" || echo "${YELLOW}${STATUS_MCP_RUNNING}${NC}")"
    echo ""

    # 推荐操作
    if [[ "$STATUS_CHROME" != "已安装" || "$STATUS_NODE" != "已安装" || "$STATUS_MCP_CONFIG" != "已配置" ]]; then
        echo -e "${YELLOW}推荐操作: 请在菜单中选择「安装 Google MCP」${NC}"
    else
        echo -e "${GREEN}所有组件已就绪，可以正常使用 Chrome DevTools MCP。${NC}"
    fi
}

# ============================================================
# 4. Chromium 安装
# ============================================================

install_chromium() {
    if [[ -n "$CHROME_BIN" ]] && [[ "${FORCE_INSTALL:-}" != "true" ]]; then
        log_success "Chromium/Chrome 已安装: ${CHROME_VERSION}"
        return 0
    fi

    log_info "正在安装 Chromium/Chrome..."

    case "$PKG_MANAGER" in
        apt)
            apt-get update -qq && $PKG_INSTALL chromium-browser
            ;;
        dnf|yum)
            # 检查 EPEL（RHEL/CentOS 需要）
            if [[ "$DISTRO_ID" =~ ^(rhel|centos|almalinux|rocky)$ ]]; then
                if ! $PKG_QUERY epel-release &>/dev/null; then
                    log_info "正在启用 EPEL 仓库..."
                    $PKG_INSTALL epel-release
                fi
            fi
            $PKG_INSTALL chromium
            if [[ "$DISTRO_ID" =~ ^(rhel|centos|almalinux|rocky)$ ]]; then
                # CentOS Stream 9 上 chromium 可能需要额外设置
                if ! has_command chromium && has_command chromium-browser; then
                    true
                fi
            fi
            ;;
        apk)
            apk update && $PKG_INSTALL chromium
            ;;
        pacman)
            $PKG_INSTALL chromium
            ;;
        *)
            log_error "不支持的发行版: ${DISTRO_ID}"
            log_info "请手动安装 Chromium/Chrome: https://www.google.com/chrome/"
            return 1
            ;;
    esac

    # 重新检测
    detect_chrome
    if [[ -z "$CHROME_BIN" ]]; then
        log_error "Chromium/Chrome 安装失败，请手动安装。"
        return 1
    fi
    log_success "Chromium/Chrome 安装成功: ${CHROME_VERSION}"
    return 0
}

# ============================================================
# 5. Node.js 安装
# ============================================================

install_nodejs() {
    if [[ -n "$NODE_BIN" ]]; then
        # 检查版本 >= 18
        local ver
        ver="$("$NODE_BIN" --version 2>/dev/null | sed 's/^v//' | cut -d. -f1)"
        if [[ "${ver:-0}" -ge 18 ]]; then
            log_success "Node.js 已安装: ${NODE_VERSION}"
            return 0
        fi
        if [[ "${FORCE_INSTALL:-}" != "true" ]]; then
            log_warn "Node.js 版本过低: ${NODE_VERSION}，需要 >= 18"
            if ! confirm "是否升级 Node.js?"; then
                return 1
            fi
        fi
    fi

    # 优先 nvm
    if [[ -d "$NVM_DIR" ]] || confirm "是否通过 nvm 安装 Node.js (推荐)?"; then
        if [[ ! -d "$NVM_DIR" ]]; then
            log_info "正在安装 nvm..."
            curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash
        fi
        if [[ -s "$NVM_DIR/nvm.sh" ]]; then
            # shellcheck source=/dev/null
            . "$NVM_DIR/nvm.sh"
            log_info "通过 nvm 安装 Node.js LTS..."
            nvm install --lts
            nvm use --lts
        fi
    fi

    # 回退：包管理器
    if ! has_command node; then
        log_info "通过包管理器安装 Node.js..."
        case "$PKG_MANAGER" in
            apt)
                apt-get update -qq && $PKG_INSTALL nodejs npm
                # Ubuntu/Debian 上的 nodejs 可能版本旧，尝试 nodesource
                local node_ver
                node_ver="$(node --version 2>/dev/null | sed 's/^v//' | cut -d. -f1)"
                if [[ "${node_ver:-0}" -lt 18 ]]; then
                    log_warn "系统包管理器 Node.js 版本过低，建议使用 nvm 安装。"
                fi
                ;;
            dnf|yum)
                $PKG_INSTALL nodejs npm
                ;;
            apk)
                apk update && $PKG_INSTALL nodejs npm
                ;;
            pacman)
                $PKG_INSTALL nodejs npm
                ;;
            *)
                log_error "不支持的发行版，请手动安装 Node.js >= 18"
                return 1
                ;;
        esac
    fi

    # 重新检测
    detect_nodejs
    if [[ -z "$NODE_BIN" ]]; then
        log_error "Node.js 安装失败。"
        return 1
    fi
    log_success "Node.js 安装成功: ${NODE_VERSION}"
    return 0
}

# ============================================================
# 6. MCP 配置
# ============================================================

get_project_root() {
    # 尝试从当前目录向上找 .claude 目录
    local dir="$PWD"
    while [[ "$dir" != "/" ]]; do
        if [[ -d "$dir/.claude" ]]; then
            echo "$dir"
            return 0
        fi
        dir="$(dirname "$dir")"
    done
    # 没找到就用 PWD
    echo "$PWD"
}

write_start_script() {
    local target_dir="$1"
    local script_path="${target_dir}/start-chrome-mcp.sh"

    log_info "生成运行时脚本: ${script_path}"

    cat > "$script_path" << 'SCRIPT'
#!/usr/bin/env bash
# ============================================================
# start-chrome-mcp.sh
# 由 setup-google-mcp.sh 自动生成
# Chrome DevTools MCP 启动脚本 - Linux 无头环境
# ============================================================
set -uo pipefail

CHROME_DEBUG_PORT="${CHROME_DEBUG_PORT:-9222}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/chrome-mcp.log"

log() { echo "[$(date '+%H:%M:%S')] $*" >> "$LOG_FILE"; }

# ── 检测 Chrome 二进制 ────────────────────────────────────
detect_chrome() {
    local candidates=("google-chrome" "google-chrome-stable" "chromium-browser" "chromium")
    for bin in "${candidates[@]}"; do
        if command -v "$bin" &>/dev/null; then
            echo "$bin"
            return 0
        fi
    done
    # 常见路径兜底
    local paths=("/usr/bin/chromium" "/usr/bin/chromium-browser" "/opt/google/chrome/chrome")
    for p in "${paths[@]}"; do
        if [[ -x "$p" ]]; then
            echo "$p"
            return 0
        fi
    done
    return 1
}

# ── 检测 npx ──────────────────────────────────────────────
detect_npx() {
    # nvm 优先
    if [[ -n "${NVM_DIR:-}" && -s "$NVM_DIR/nvm.sh" ]]; then
        # shellcheck source=/dev/null
        . "$NVM_DIR/nvm.sh"
        command -v npx 2>/dev/null && return 0
    fi
    command -v npx 2>/dev/null && return 0
    # 常见路径
    local paths=("/usr/bin/npx" "/usr/local/bin/npx" "/usr/lib/node_modules/npm/bin/npx-cli.js")
    for p in "${paths[@]}"; do
        if [[ -x "$p" ]]; then
            echo "$p"
            return 0
        fi
    done
    return 1
}

# ── 清理 ──────────────────────────────────────────────────
cleanup() {
    log "正在清理进程..."
    if [[ -n "${CHROME_PID:-}" ]]; then
        kill "$CHROME_PID" 2>/dev/null || true
        wait "$CHROME_PID" 2>/dev/null || true
    fi
    log "清理完成"
}
trap cleanup EXIT INT TERM

# ── 主流程 ────────────────────────────────────────────────
CHROME_BIN="$(detect_chrome)"
if [[ -z "$CHROME_BIN" ]]; then
    log "错误: 未找到 Chrome/Chromium 二进制"
    echo "ERROR: Chrome/Chromium not found" >> "$LOG_FILE"
    exit 1
fi
log "使用 Chrome: $CHROME_BIN"

NPX_BIN="$(detect_npx)"
if [[ -z "$NPX_BIN" ]]; then
    log "错误: 未找到 npx"
    echo "ERROR: npx not found" >> "$LOG_FILE"
    exit 1
fi
log "使用 npx: $NPX_BIN"

# ── 启动 headless Chrome ─────────────────────────────────
CHROME_ARGS=(
    --headless
    --no-sandbox
    --disable-gpu
    --disable-dev-shm-usage
    --remote-debugging-port="$CHROME_DEBUG_PORT"
    --remote-debugging-address=0.0.0.0
    --window-size=1920,1080
    --hide-scrollbars
)

# 检查是否已经在运行
if curl -sf "http://127.0.0.1:${CHROME_DEBUG_PORT}/json/version" >/dev/null 2>&1; then
    log "Chrome DevTools 已在端口 ${CHROME_DEBUG_PORT} 上运行"
    log "跳过 Chrome 启动"
else
    log "启动 Chrome (headless, 端口 ${CHROME_DEBUG_PORT})..."
    "$CHROME_BIN" "${CHROME_ARGS[@]}" &>/tmp/chromium-mcp.log &
    CHROME_PID=$!

    # 等待 DevTools 就绪
    for i in {1..15}; do
        if curl -sf "http://127.0.0.1:${CHROME_DEBUG_PORT}/json/version" >/dev/null 2>&1; then
            log "Chrome DevTools 就绪 (${i}s)"
            break
        fi
        sleep 1
    done

    if ! curl -sf "http://127.0.0.1:${CHROME_DEBUG_PORT}/json/version" >/dev/null 2>&1; then
        log "错误: Chrome DevTools 启动超时"
        echo "ERROR: Chrome DevTools timeout" >> "$LOG_FILE"
        exit 1
    fi
fi

# ── 启动 chrome-devtools-mcp ──────────────────────────────
log "启动 chrome-devtools-mcp..."
exec "$NPX_BIN" chrome-devtools-mcp@latest \
    --port "$CHROME_DEBUG_PORT" \
    --headless \
    --no-usage-statistics
SCRIPT

    chmod +x "$script_path"
    log_success "运行时脚本已生成: ${script_path}"
}

setup_mcp_config() {
    local project_root
    project_root="$(get_project_root)"
    local start_script_path="${project_root}/.claude/start-chrome-mcp.sh"
    local project_settings="${project_root}/.claude/settings.local.json"

    # 创建目录
    mkdir -p "$(dirname "$start_script_path")"
    mkdir -p "$GLOBAL_SCRIPTS_DIR"

    # 1. 生成运行时脚本
    write_start_script "$(dirname "$start_script_path")"

    # 2. 复制到全局（给 Claude Code 用）
    cp "$start_script_path" "${GLOBAL_SCRIPTS_DIR}/start-chrome-mcp.sh"
    chmod +x "${GLOBAL_SCRIPTS_DIR}/start-chrome-mcp.sh"

    # 3. 配置全局 mcp.json
    log_info "配置 MCP JSON..."
    mkdir -p "$(dirname "$GLOBAL_MCP_JSON")"

    python3 -c '
import json, sys, os

filepath = sys.argv[1]
start_script = sys.argv[2]

data = {}
if os.path.exists(filepath):
    with open(filepath) as f:
        data = json.load(f)

data.setdefault("mcpServers", {})
data["mcpServers"]["chrome-devtools"] = {
    "command": "bash",
    "args": [start_script]
}

with open(filepath, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
' "$GLOBAL_MCP_JSON" "${GLOBAL_SCRIPTS_DIR}/start-chrome-mcp.sh"

    log_success "MCP JSON 已更新: ${GLOBAL_MCP_JSON}"

    # 4. 配置项目 settings.local.json
    log_info "配置项目 MCP 设置..."
    mkdir -p "$(dirname "$project_settings")"

    python3 -c '
import json, sys, os

filepath = sys.argv[1]

data = {}
if os.path.exists(filepath):
    with open(filepath) as f:
        data = json.load(f)

enabled = data.setdefault("enabledMcpjsonServers", [])
if "chrome-devtools" not in enabled:
    enabled.append("chrome-devtools")

with open(filepath, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
' "$project_settings"

    log_success "项目设置已更新: ${project_settings}"
    return 0
}

# ============================================================
# 7. 功能验证
# ============================================================

verify_all() {
    local failed=0

    log_title "🔍 正在验证安装"

    # 测试 1: Chromium 无头模式
    echo -n "  Chromium 无头模式 ... "
    if [[ -n "$CHROME_BIN" ]]; then
        local test_output
        test_output="$("$CHROME_BIN" --headless --no-sandbox --disable-gpu --dump-dom about:blank 2>/dev/null | head -5)"
        if echo "$test_output" | grep -qi "<html\|<!DOCTYPE\|<head\|<body"; then
            echo -e "${GREEN}通过${NC}"
        else
            echo -e "${YELLOW}警告 (输出不完整，但 Chrome 可启动)${NC}"
        fi
    else
        echo -e "${RED}跳过 (Chrome 未安装)${NC}"
        ((failed++))
    fi

    # 测试 2: DevTools 协议
    echo -n "  DevTools 协议       ... "
    if [[ -n "$CHROME_BIN" ]]; then
        # 在随机端口上启动测试实例
        local test_port=19222
        "$CHROME_BIN" --headless --no-sandbox --disable-gpu --remote-debugging-port="$test_port" &
        local chrome_test_pid=$!
        sleep 2
        if curl -sf "http://127.0.0.1:${test_port}/json/version" >/dev/null 2>&1; then
            echo -e "${GREEN}通过${NC}"
        else
            echo -e "${RED}失败${NC}"
            ((failed++))
        fi
        kill "$chrome_test_pid" 2>/dev/null || true
        wait "$chrome_test_pid" 2>/dev/null || true
    else
        echo -e "${RED}跳过 (Chrome 未安装)${NC}"
    fi

    # 测试 3: chrome-devtools-mcp
    echo -n "  chrome-devtools-mcp  ... "
    if [[ -n "$NPX_BIN" ]]; then
        if "$NPX_BIN" chrome-devtools-mcp@latest --help 2>/dev/null | head -3 | grep -qi "chrome\|devtools\|mcp"; then
            echo -e "${GREEN}通过${NC}"
        else
            # npx 可能在 stderr 输出缓存信息
            local npx_out
            npx_out="$("$NPX_BIN" chrome-devtools-mcp@latest --help 2>&1 | head -5)"
            if echo "$npx_out" | grep -qi "Usage\|Options\|chrome\|devtools"; then
                echo -e "${GREEN}通过${NC}"
            else
                echo -e "${YELLOW}警告 (可能需要网络下载)${NC}"
                echo "    $npx_out"
            fi
        fi
    else
        echo -e "${RED}跳过 (npx 未安装)${NC}"
        ((failed++))
    fi

    echo ""
    if [[ $failed -eq 0 ]]; then
        log_success "全部验证通过"
        return 0
    else
        log_warn "${failed} 项验证有问题"
        return 1
    fi
}

# ============================================================
# 8. 安装主流程
# ============================================================

install_all() {
    detect_all

    local steps=5
    local current=0

    clear
    log_title "📦 开始安装 Google MCP"

    ((current++))
    log_step "${current}/${steps}" "检测系统环境"
    detect_system
    detect_env
    echo "  系统: ${DISTRO:-未知} | ${ARCH} | $([ "$IS_CONTAINER" = true ] && echo "容器" || echo "宿主")"
    log_success "环境检测完成"

    ((current++))
    log_step "${current}/${steps}" "安装 Chromium/Chrome"
    install_chromium || log_warn "Chromium 安装有问题，继续后续步骤..."

    ((current++))
    log_step "${current}/${steps}" "安装 Node.js"
    install_nodejs || log_warn "Node.js 安装有问题，继续后续步骤..."

    ((current++))
    log_step "${current}/${steps}" "配置 MCP"
    setup_mcp_config || log_warn "MCP 配置有问题，继续后续步骤..."

    ((current++))
    log_step "${current}/${steps}" "验证安装"
    detect_all
    verify_all || true

    echo ""
    if [[ "$STATUS_MCP_CONFIG" == "已配置" && "$STATUS_CHROME" == "已安装" && "$STATUS_NODE" == "已安装" ]]; then
        log_success "Google MCP 安装完成！"
        echo ""
        echo "  下一步:"
        echo "  1. 重启 Claude Code 以加载新 MCP 配置"
        echo "  2. 运行 'bash $0 --detect' 确认状态"
    else
        log_warn "安装部分完成，请检查上方日志中的警告。"
    fi
}

# ============================================================
# 9. 卸载主流程
# ============================================================

remove_mcp_config() {
    local project_root
    project_root="$(get_project_root)"
    local project_settings="${project_root}/.claude/settings.local.json"
    local start_script="${project_root}/.claude/start-chrome-mcp.sh"

    log_info "清理 MCP 配置..."

    # 从全局 mcp.json 移除
    if [[ -f "$GLOBAL_MCP_JSON" ]]; then
        python3 -c '
import json, sys, os
filepath = sys.argv[1]
if os.path.exists(filepath):
    with open(filepath) as f:
        data = json.load(f)
    data.get("mcpServers", {}).pop("chrome-devtools", None)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("已移除 chrome-devtools 条目")
' "$GLOBAL_MCP_JSON"
        log_success "已更新: ${GLOBAL_MCP_JSON}"
    fi

    # 从项目 settings 移除
    if [[ -f "$project_settings" ]]; then
        python3 -c '
import json, sys, os
filepath = sys.argv[1]
if os.path.exists(filepath):
    with open(filepath) as f:
        data = json.load(f)
    enabled = data.get("enabledMcpjsonServers", [])
    if "chrome-devtools" in enabled:
        enabled.remove("chrome-devtools")
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("已从 enabledMcpjsonServers 移除 chrome-devtools")
' "$project_settings"
        log_success "已更新: ${project_settings}"
    fi

    # 删除运行时脚本
    if [[ -f "$start_script" ]]; then
        rm -f "$start_script"
        log_success "已删除: ${start_script}"
    fi

    # 删除全局运行时脚本
    local global_script="${GLOBAL_SCRIPTS_DIR}/start-chrome-mcp.sh"
    if [[ -f "$global_script" ]]; then
        rm -f "$global_script"
        log_success "已删除: ${global_script}"
    fi

    # 尝试杀掉 Chrome DevTools 进程
    if curl -sf "http://127.0.0.1:${CHROME_DEBUG_PORT}/json/version" >/dev/null 2>&1; then
        log_info "检测到 Chrome DevTools 正在运行 (端口 ${CHROME_DEBUG_PORT})"
        if confirm "是否关闭 Chrome DevTools?"; then
            # 查找并 kill 监听该端口的 Chrome 进程
            local chrome_pids
            chrome_pids="$(lsof -ti:"${CHROME_DEBUG_PORT}" 2>/dev/null || ss -tlnp "sport = :${CHROME_DEBUG_PORT}" 2>/dev/null | grep -oP 'pid=\K\d+' || true)"
            if [[ -n "$chrome_pids" ]]; then
                kill $chrome_pids 2>/dev/null || true
                log_success "Chrome DevTools 已关闭"
            fi
        fi
    fi

    log_success "MCP 清理完成"
}

uninstall_chrome() {
    if [[ -z "$CHROME_BIN" ]]; then
        log_warn "Chromium/Chrome 未安装，跳过"
        return 0
    fi

    log_warn "将卸载: ${CHROME_BIN} (${CHROME_VERSION})"
    if ! confirm "确认卸载 Chromium/Chrome?"; then
        log_info "跳过 Chromium 卸载"
        return 0
    fi

    # 先杀掉相关进程
    local pids
    pids="$(pgrep -f "$CHROME_BIN" 2>/dev/null || true)"
    if [[ -n "$pids" ]]; then
        log_info "正在关闭 Chrome 进程..."
        kill $pids 2>/dev/null || true
        sleep 1
    fi

    # 根据包管理器卸载
    case "$PKG_MANAGER" in
        apt)
            # 找出实际安装的包名
            local pkg_name
            if dpkg -l chromium-browser &>/dev/null; then
                pkg_name="chromium-browser"
            elif dpkg -l google-chrome-stable &>/dev/null; then
                pkg_name="google-chrome-stable"
            else
                pkg_name="chromium-browser"
            fi
            apt-get remove -y "$pkg_name"
            ;;
        dnf|yum)
            local pkg_name="chromium"
            rpm -q google-chrome-stable &>/dev/null && pkg_name="google-chrome-stable"
            $PKG_INSTALL remove -y "$pkg_name"
            ;;
        apk)
            apk del chromium
            ;;
        pacman)
            pacman -Rs --noconfirm chromium
            ;;
        *)
            log_warn "不支持的包管理器，请手动卸载 Chrome"
            return 1
            ;;
    esac

    log_success "Chromium/Chrome 已卸载"
    return 0
}

uninstall_nodejs() {
    if [[ -z "$NODE_BIN" ]]; then
        log_warn "Node.js 未安装，跳过"
        return 0
    fi

    log_warn "将卸载: Node.js (${NODE_VERSION})"
    if ! confirm "确认卸载 Node.js?"; then
        log_info "跳过 Node.js 卸载"
        return 0
    fi

    # nvm 管理的
    if [[ -s "$NVM_DIR/nvm.sh" ]]; then
        if confirm "Node.js 由 nvm 管理，是否同时移除 nvm?"; then
            rm -rf "$NVM_DIR"
            log_success "nvm 及管理的 Node.js 已移除"
            # 从 bashrc 清理
            sed -i '/NVM_DIR/d' ~/.bashrc 2>/dev/null || true
            sed -i '/nvm.sh/d' ~/.bashrc 2>/dev/null || true
            return 0
        else
            log_info "保留 nvm 和 Node.js"
            return 0
        fi
    fi

    # 系统包管理器安装的
    case "$PKG_MANAGER" in
        apt)
            apt-get remove -y nodejs npm 2>/dev/null || true
            ;;
        dnf|yum)
            $PKG_INSTALL remove -y nodejs npm 2>/dev/null || true
            ;;
        apk)
            apk del nodejs npm 2>/dev/null || true
            ;;
        pacman)
            pacman -Rs --noconfirm nodejs npm 2>/dev/null || true
            ;;
        *)
            log_warn "请手动卸载 Node.js"
            return 1
            ;;
    esac

    log_success "Node.js 已卸载"
    return 0
}

uninstall_all() {
    detect_all

    clear
    log_title "🗑 卸载 Google MCP"

    echo -e "${YELLOW}注意: 卸载操作将移除相关组件。输入 y 确认每个步骤。${NC}"
    echo ""

    # 1. 移除 MCP 配置
    if [[ "$STATUS_MCP_CONFIG" == "已配置" ]]; then
        log_step "1/3" "移除 MCP 配置"
        remove_mcp_config
    else
        log_info "MCP 未配置，跳过"
    fi

    # 2. 卸载 Node.js
    echo ""
    log_step "2/3" "卸载 Node.js"
    uninstall_nodejs

    # 3. 卸载 Chromium
    echo ""
    log_step "3/3" "卸载 Chromium/Chrome"
    uninstall_chrome

    echo ""
    log_success "卸载操作完成"

    # 最终检测
    detect_all
    show_report
}

# ============================================================
# 10. 命令行参数解析
# ============================================================

usage() {
    cat << EOF
用法: $(basename "$0") [选项]

选项:
  --install      直接安装 Google MCP（非交互式）
  --uninstall    直接卸载 Google MCP（非交互式）
  --detect       检测当前环境（非交互式）
  --force        强制重装（配合 --install 使用）
  --port PORT    指定 Chrome DevTools 调试端口（默认 9222）
  --help         显示此帮助信息

示例:
  $(basename "$0")                  交互式菜单
  $(basename "$0") --install        自动安装
  $(basename "$0") --install --force 强制重装
  $(basename "$0") --detect         检测环境
  $(basename "$0") --uninstall      自动卸载
EOF
    exit 0
}

parse_args() {
    local mode="menu"
    FORCE_INSTALL="false"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --install)    mode="install" ;;
            --uninstall)  mode="uninstall" ;;
            --detect)     mode="detect" ;;
            --force)      FORCE_INSTALL="true" ;;
            --port)
                shift
                CHROME_DEBUG_PORT="${1:-9222}"
                ;;
            --help|-h)    usage ;;
            *)
                log_error "未知参数: $1"
                usage
                ;;
        esac
        shift
    done

    echo "$mode"
}

# ============================================================
# 11. 主入口
# ============================================================

main() {
    # --help 在 $() 子 shell 外提前处理
    for arg in "$@"; do
        if [[ "$arg" == "--help" || "$arg" == "-h" ]]; then
            usage
        fi
    done

    local mode
    mode="$(parse_args "$@")"

    detect_all

    case "$mode" in
        install)
            install_all
            ;;
        uninstall)
            uninstall_all
            ;;
        detect)
            clear
            show_report
            ;;
        menu)
            # 仅在无参数交互菜单模式下检查终端
            if [[ ! -t 0 ]]; then
                clear
                show_report
                exit 0
            fi
            show_menu
            ;;
    esac
}

main "$@"

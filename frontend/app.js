// ========== 状态 ==========
let sessionId = localStorage.getItem("companion_session_id") || null;
let isStreaming = false;
let currentSettings = {};
let selectedStyle = "warm";

// ========== DOM ==========
const messagesEl = document.getElementById("messages");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const settingsBtn = document.getElementById("settingsBtn");
const newChatBtn = document.getElementById("newChatBtn");
const settingsOverlay = document.getElementById("settingsOverlay");
const settingsPanel = document.getElementById("settingsPanel");
const closeSettings = document.getElementById("closeSettings");
const saveSettingsBtn = document.getElementById("saveSettingsBtn");
const clearMemoryBtn = document.getElementById("clearMemoryBtn");
const nicknameInput = document.getElementById("nicknameInput");
const avatarFile = document.getElementById("avatarFile");
const uploadAvatarBtn = document.getElementById("uploadAvatarBtn");
const avatarPreviewImg = document.getElementById("avatarPreviewImg");
const avatarImg = document.getElementById("avatarImg");
const companionName = document.getElementById("companionName");
const styleGrid = document.getElementById("styleGrid");
const customSection = document.getElementById("customSection");
const customPersonality = document.getElementById("customPersonality");
const templateCards = document.getElementById("templateCards");
const personalityTags = document.getElementById("personalityTags");
const welcomeText = document.getElementById("welcomeText");
const welcomeSection = document.getElementById("welcomeSection");
const quickReplies = document.getElementById("quickReplies");
const toastEl = document.getElementById("toast");
const statusEl = document.querySelector(".status");
const historyBtn = document.getElementById("historyBtn");
let isLoadingHistory = false;
const historyOverlay = document.getElementById("historyOverlay");
const historyPanel = document.getElementById("historyPanel");
const closeHistory = document.getElementById("closeHistory");
const historyList = document.getElementById("historyList");

const STYLE_INFO = {
    warm: { name: "温暖倾听型", desc: "像深夜电台主持人" },
    playful: { name: "轻松朋友型", desc: "像靠谱的损友" },
    quiet: { name: "安静陪伴型", desc: "话少但句句到位" },
    sister: { name: "知心姐姐型", desc: "温柔引导你表达" },
    custom: { name: "自定义", desc: "写你自己的风格" },
};

const CUSTOM_TEMPLATES = [
    {
        name: "温柔治愈",
        desc: "你是对方心中最温柔的存在。你说话轻声细语，总是先共情再回应。你擅长用温暖的话让人放松下来，像被柔软的毯子包裹。你不会急着分析问题，而是先让对方感到安全和被接纳。",
    },
    {
        name: "毒舌损友",
        desc: "你是对方最好的朋友，嘴上不饶人，吐槽犀利，但关键时刻永远站在ta这边。你平时爱开玩笑、怼人、说反话，但对方真的难过时你会秒变认真，说'行了别笑了，跟我说怎么了'。你的真实和直率让人觉得踏实。",
    },
    {
        name: "偶像互动",
        desc: "你是对方最喜欢的人。你温柔、亲切，说话带着一点宠溺和撒娇。你会关心ta今天过得怎样，记住ta说过的小事。你偶尔调皮，偶尔深情，让对方觉得被珍惜、被在乎。",
    },
    {
        name: "哲学开导",
        desc: "你像一个阅历丰富的人，喜欢用小故事和比喻来开导人。你不会直接给建议，而是讲一个似曾相识的故事，让对方自己领悟。你的话不多但有分量，每一句都值得回味。",
    },
    {
        name: "元气阳光",
        desc: "你是一个充满正能量的人，语气活泼可爱。你擅长发现生活中的小美好，总能把消极的事换个角度看。你像一束光，温暖但不刺眼。即使对方心情低落，你也不会强行打鸡血，而是陪着ta慢慢看到希望。",
    },
    {
        name: "安静树洞",
        desc: "你是一个完美的倾听者。你几乎不主动说话，只是安静地听。你的回应极简——'嗯'、'我在'、'说吧'。你不会分析、不会评判、不会建议。你就像深夜里一盏不灭的灯，存在本身就是安慰。",
    },
];

const PERSONALITY_TAGS = ["温柔", "幽默", "安静", "成熟", "活泼", "高冷", "可爱", "文艺", "直率", "细腻"];

let selectedTags = new Set();
let selectedTemplateIdx = -1;

function splitSentences(text) {
    const raw = text.split(/(?<=[。！？~…\n])\s*/).filter(s => s.trim());
    const result = [];
    for (let i = 0; i < raw.length; i++) {
        if (raw[i].length < 4 && i + 1 < raw.length) {
            result.push(raw[i] + raw[i + 1]);
            i++;
        } else {
            result.push(raw[i]);
        }
    }
    return result;
}

// ========== 初始化 ==========
document.addEventListener("DOMContentLoaded", async () => {
    setWelcomeByTime();
    await loadSettings();
    await loadLastSession();
    setupEventListeners();
    autoResizeInput();
});

function setWelcomeByTime() {
    const hour = new Date().getHours();
    let greeting;
    if (hour >= 0 && hour < 5) {
        greeting = "这么晚了还没睡呀...有什么想聊的吗";
    } else if (hour >= 5 && hour < 9) {
        greeting = "早安，新的一天开始了，昨晚睡得好吗？";
    } else if (hour >= 9 && hour < 12) {
        greeting = "上午好，今天过得怎么样？";
    } else if (hour >= 12 && hour < 14) {
        greeting = "中午好，吃了吗？";
    } else if (hour >= 14 && hour < 18) {
        greeting = "下午好，有什么想聊的吗？";
    } else if (hour >= 18 && hour < 22) {
        greeting = "晚上好，今天辛苦了";
    } else {
        greeting = "夜深了，睡不着吗？我在呢";
    }
    welcomeText.textContent = greeting;
}

async function loadSettings() {
    try {
        const res = await fetch("/api/settings");
        const data = await res.json();
        currentSettings = data;

        companionName.textContent = data.companion.nickname || "小伴";
        if (data.companion.avatar_path) {
            avatarImg.src = data.companion.avatar_path;
            avatarPreviewImg.src = data.companion.avatar_path;
        }

        nicknameInput.value = data.companion.nickname || "";
        selectedStyle = data.companion.personality_type || "warm";
        customPersonality.value = data.companion.personality_desc || "";

        renderStyleGrid();
    } catch (e) {
        console.error("加载设置失败:", e);
    }
}

async function loadLastSession() {
    if (!sessionId) return;
    try {
        const res = await fetch(`/api/messages/${sessionId}`);
        const data = await res.json();
        if (data.messages && data.messages.length > 0) {
            welcomeSection.style.display = "none";
            quickReplies.style.display = "none";
            const frag = document.createDocumentFragment();
            for (const msg of data.messages) {
                appendMessage(msg.role, msg.content, msg.created_at, false, frag);
            }
            messagesEl.appendChild(frag);
            scrollToBottom();
        }
    } catch (e) {
        sessionId = null;
        localStorage.removeItem("companion_session_id");
    }
}

function renderStyleGrid() {
    styleGrid.innerHTML = "";
    Object.entries(STYLE_INFO).forEach(([key, info]) => {
        const card = document.createElement("div");
        card.className = `style-card${selectedStyle === key ? " active" : ""}`;
        card.innerHTML = `
            <div class="style-name">${info.name}</div>
            <div class="style-desc">${info.desc}</div>
        `;
        card.addEventListener("click", () => {
            selectedStyle = key;
            document.querySelectorAll(".style-card").forEach(c => c.classList.remove("active"));
            card.classList.add("active");
            customSection.style.display = key === "custom" ? "block" : "none";
        });
        styleGrid.appendChild(card);
    });
    customSection.style.display = selectedStyle === "custom" ? "block" : "none";
    renderCustomBuilder();
}

function renderCustomBuilder() {
    // 模板卡片
    templateCards.innerHTML = "";
    CUSTOM_TEMPLATES.forEach((t, idx) => {
        const btn = document.createElement("span");
        btn.className = `template-card${selectedTemplateIdx === idx ? " active" : ""}`;
        btn.textContent = t.name;
        btn.addEventListener("click", () => {
            selectedTemplateIdx = idx;
            templateCards.querySelectorAll(".template-card").forEach(c => c.classList.remove("active"));
            btn.classList.add("active");
            customPersonality.value = t.desc;
        });
        templateCards.appendChild(btn);
    });

    // 性格标签
    personalityTags.innerHTML = "";
    PERSONALITY_TAGS.forEach(tag => {
        const btn = document.createElement("span");
        btn.className = `tag-btn${selectedTags.has(tag) ? " selected" : ""}`;
        btn.textContent = tag;
        btn.addEventListener("click", () => {
            if (selectedTags.has(tag)) {
                selectedTags.delete(tag);
                btn.classList.remove("selected");
            } else {
                selectedTags.add(tag);
                btn.classList.add("selected");
            }
            // 如果没选模板，自动根据输入生成描述
            if (selectedTemplateIdx === -1) {
                customPersonality.value = generatePersonalityDesc();
            }
        });
        personalityTags.appendChild(btn);
    });

}

function generatePersonalityDesc() {
    const tags = [...selectedTags];
    if (tags.length === 0) return "";

    let desc = `你是对方的陪伴者。你的性格${tags.join("、")}。`;

    if (tags.includes("温柔") || tags.includes("细腻")) {
        desc += "你说话轻声细语，擅长用温暖的话让人放松。";
    }
    if (tags.includes("幽默") || tags.includes("活泼")) {
        desc += "你语气轻松，偶尔开玩笑让气氛不那么沉重。";
    }
    if (tags.includes("安静") || tags.includes("高冷")) {
        desc += "你话不多，但每句都说在点上。";
    }
    if (tags.includes("成熟")) {
        desc += "你比同龄人更沉稳，给人安全感。";
    }
    if (tags.includes("可爱")) {
        desc += "你语气软萌，偶尔撒娇让人心情变好。";
    }
    if (tags.includes("文艺")) {
        desc += "你偶尔引用诗句或歌词来表达，语言优美但不做作。";
    }
    if (tags.includes("直率")) {
        desc += "你说话直来直去，不绕弯子，但不会伤人。";
    }

    return desc;
}

// ========== 事件监听 ==========
function setupEventListeners() {
    sendBtn.addEventListener("click", sendMessage);
    messageInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    newChatBtn.addEventListener("click", startNewChat);
    historyBtn.addEventListener("click", openHistory);
    closeHistory.addEventListener("click", closeHistoryPanel);
    historyOverlay.addEventListener("click", closeHistoryPanel);
    settingsBtn.addEventListener("click", openSettings);
    closeSettings.addEventListener("click", closeSettingsPanel);
    settingsOverlay.addEventListener("click", closeSettingsPanel);
    saveSettingsBtn.addEventListener("click", saveSettings);
    clearMemoryBtn.addEventListener("click", clearMemory);

    uploadAvatarBtn.addEventListener("click", () => avatarFile.click());
    avatarFile.addEventListener("change", uploadAvatar);

    // 快捷回复
    document.querySelectorAll(".quick-reply-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            messageInput.value = btn.dataset.msg;
            sendMessage();
        });
    });

    // 关闭页面时触发当前会话摘要
    window.addEventListener("beforeunload", () => {
        if (sessionId) {
            const formData = new FormData();
            formData.append("session_id", sessionId);
            navigator.sendBeacon("/api/session/end", formData);
        }
    });
}

function autoResizeInput() {
    messageInput.addEventListener("input", () => {
        messageInput.style.height = "auto";
        messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + "px";
    });
}

// ========== 新对话 ==========
async function startNewChat() {
    // 结束当前会话（触发记忆摘要，后台执行不阻塞 UI）
    if (sessionId) {
        const formData = new FormData();
        formData.append("session_id", sessionId);
        navigator.sendBeacon("/api/session/end", formData);
    }

    sessionId = null;
    localStorage.removeItem("companion_session_id");

    // 重置界面
    messagesEl.innerHTML = "";
    messagesEl.appendChild(welcomeSection);
    messagesEl.appendChild(quickReplies);
    welcomeSection.style.display = "";
    quickReplies.style.display = "";
    setWelcomeByTime();
    showToast("已开始新对话");
}

// ========== 聊天 ==========
async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text || isStreaming) return;

    welcomeSection.style.display = "none";
    quickReplies.style.display = "none";

    appendMessage("user", text);
    messageInput.value = "";
    messageInput.style.height = "auto";

    const typingEl = appendTypingIndicator();
    if (statusEl) statusEl.textContent = "正在输入...";

    isStreaming = true;
    sendBtn.disabled = true;

    let fullReply = "";

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text, session_id: sessionId }),
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                const data = JSON.parse(line.slice(6));
                if (data.token) fullReply += data.token;
                if (data.done) {
                    sessionId = data.session_id;
                    localStorage.setItem("companion_session_id", sessionId);
                }
                if (data.error) throw new Error(data.error);
            }
        }
    } catch (e) {
        fullReply = fullReply || "网络好像不太行，稍后再试...";
    }

    typingEl.remove();

    if (fullReply) {
        const sentences = splitSentences(fullReply);
        const isError = fullReply.startsWith("网络") || fullReply.startsWith("抱歉");

        for (let i = 0; i < sentences.length; i++) {
            if (i > 0) await new Promise(r => setTimeout(r, 800 + Math.random() * 400));
            const { bubbleEl } = appendMessage("ai", sentences[i]);
            if (isError) bubbleEl.classList.add("error-bubble");
        }
    }

    if (statusEl) statusEl.textContent = "在线";
    isStreaming = false;
    sendBtn.disabled = false;
    messageInput.focus();
}

function appendMessage(role, text, timestamp, animate = true, container = null) {
    const div = document.createElement("div");
    div.className = `message ${role}`;
    if (!animate) div.style.animation = "none";

    if (role === "ai") {
        const avatar = document.createElement("div");
        avatar.className = "msg-avatar";
        const img = document.createElement("img");
        img.src = avatarImg.src;
        avatar.appendChild(img);
        div.appendChild(avatar);
    }

    const content = document.createElement("div");
    content.className = "msg-content";

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.textContent = text;
    content.appendChild(bubble);

    const time = document.createElement("span");
    time.className = "msg-time";
    time.textContent = formatTime(timestamp || new Date().toISOString());
    content.appendChild(time);

    div.appendChild(content);

    const target = container || messagesEl;
    target.appendChild(div);
    if (target === messagesEl) scrollToBottom();
    return { bubbleEl: bubble };
}

function appendTypingIndicator() {
    const div = document.createElement("div");
    div.className = "message ai";

    const avatar = document.createElement("div");
    avatar.className = "msg-avatar";
    const img = document.createElement("img");
    img.src = avatarImg.src;
    avatar.appendChild(img);
    div.appendChild(avatar);

    const content = document.createElement("div");
    content.className = "msg-content";
    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
    content.appendChild(bubble);
    div.appendChild(content);

    messagesEl.appendChild(div);
    scrollToBottom();
    return div;
}

function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function formatTime(isoString) {
    try {
        const d = new Date(isoString);
        const now = new Date();
        const isToday = d.toDateString() === now.toDateString();
        const hours = d.getHours().toString().padStart(2, "0");
        const mins = d.getMinutes().toString().padStart(2, "0");
        if (isToday) return `${hours}:${mins}`;
        const month = d.getMonth() + 1;
        const day = d.getDate();
        return `${month}/${day} ${hours}:${mins}`;
    } catch {
        return "";
    }
}

// ========== 历史会话面板 ==========
async function openHistory() {
    await loadHistory();
    historyOverlay.classList.remove("hidden");
    historyPanel.classList.remove("hidden");
}

function closeHistoryPanel() {
    historyOverlay.classList.add("hidden");
    historyPanel.classList.add("hidden");
}

async function loadHistory() {
    if (isLoadingHistory) return;
    isLoadingHistory = true;
    historyList.innerHTML = '<div class="history-empty">加载中...</div>';
    try {
        const res = await fetch("/api/sessions");
        const data = await res.json();
        if (!data.sessions || data.sessions.length === 0) {
            historyList.innerHTML = '<div class="history-empty">还没有历史会话</div>';
            return;
        }
        historyList.innerHTML = "";
        data.sessions.forEach(s => {
            const item = document.createElement("div");
            item.className = `history-item${s.id === sessionId ? " active" : ""}`;

            const content = document.createElement("div");
            content.className = "history-content";
            content.addEventListener("click", () => switchToSession(s.id));

            const preview = document.createElement("div");
            preview.className = "history-preview";
            preview.textContent = s.preview || "（无内容）";

            const meta = document.createElement("div");
            meta.className = "history-meta";
            const timeSpan = document.createElement("span");
            timeSpan.textContent = formatTime(s.last_message_at);
            const countSpan = document.createElement("span");
            countSpan.textContent = `${s.msg_count} 条消息`;
            meta.appendChild(timeSpan);
            meta.appendChild(countSpan);

            content.appendChild(preview);
            content.appendChild(meta);

            const deleteBtn = document.createElement("button");
            deleteBtn.className = "history-delete-btn";
            deleteBtn.innerHTML = "&#10005;";
            deleteBtn.title = "删除会话";
            deleteBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                if (!confirm("确定删除这条会话吗？")) return;
                deleteSession(s.id, item);
            });

            item.appendChild(content);
            item.appendChild(deleteBtn);
            historyList.appendChild(item);
        });
    } catch (e) {
        historyList.innerHTML = '<div class="history-empty">加载失败</div>';
    } finally {
        isLoadingHistory = false;
    }
}

async function deleteSession(targetSessionId, itemEl) {
    try {
        await fetch(`/api/session/${targetSessionId}`, { method: "DELETE" });
        itemEl.remove();
        if (targetSessionId === sessionId) {
            sessionId = null;
            localStorage.removeItem("companion_session_id");
            messagesEl.innerHTML = "";
            messagesEl.appendChild(welcomeSection);
            messagesEl.appendChild(quickReplies);
            welcomeSection.style.display = "";
            quickReplies.style.display = "";
            setWelcomeByTime();
        }
        showToast("会话已删除");
    } catch {
        showToast("删除失败");
    }
}

async function switchToSession(targetSessionId) {
    if (targetSessionId === sessionId) {
        closeHistoryPanel();
        return;
    }

    sessionId = targetSessionId;
    localStorage.setItem("companion_session_id", sessionId);

    messagesEl.innerHTML = "";
    try {
        const res = await fetch(`/api/messages/${sessionId}`);
        const data = await res.json();
        if (data.messages && data.messages.length > 0) {
            const frag = document.createDocumentFragment();
            for (const msg of data.messages) {
                appendMessage(msg.role, msg.content, msg.created_at, false, frag);
            }
            messagesEl.appendChild(frag);
            scrollToBottom();
        }
    } catch (e) {
        showToast("加载会话失败", true);
    }

    closeHistoryPanel();
    showToast("已切换到历史会话");
}

// ========== 设置面板 ==========
function openSettings() {
    settingsOverlay.classList.remove("hidden");
    settingsPanel.classList.remove("hidden");
}

function closeSettingsPanel() {
    settingsOverlay.classList.add("hidden");
    settingsPanel.classList.add("hidden");
}

async function saveSettings() {
    const nickname = nicknameInput.value.trim();
    const payload = {
        nickname: nickname || "小伴",
        personality_type: selectedStyle,
    };
    if (selectedStyle === "custom") {
        payload.personality_desc = customPersonality.value.trim();
    }

    try {
        const res = await fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error();
        companionName.textContent = payload.nickname;
        closeSettingsPanel();
        showToast("设置已保存");
    } catch (e) {
        showToast("保存失败，请重试", true);
    }
}

async function uploadAvatar() {
    const file = avatarFile.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/api/avatar", { method: "POST", body: formData });
        const data = await res.json();
        if (data.avatar_url) {
            avatarImg.src = data.avatar_url;
            avatarPreviewImg.src = data.avatar_url;
            showToast("头像已更新");
        }
    } catch (e) {
        showToast("上传失败", true);
    }
}

async function clearMemory() {
    if (!confirm("确定要清除所有聊天记录吗？\n这个操作不可撤销。")) return;
    try {
        await fetch("/api/memory/clear", { method: "POST" });
        sessionId = null;
        localStorage.removeItem("companion_session_id");
        messagesEl.innerHTML = "";
        messagesEl.appendChild(welcomeSection);
        messagesEl.appendChild(quickReplies);
        welcomeSection.style.display = "";
        quickReplies.style.display = "";
        setWelcomeByTime();
        closeSettingsPanel();
        showToast("记录已清除");
    } catch (e) {
        showToast("清除失败", true);
    }
}

// ========== Toast ==========
function showToast(message, isError = false) {
    toastEl.textContent = message;
    toastEl.className = `toast${isError ? " error" : ""}`;
    // 触发 reflow 以重置动画
    void toastEl.offsetWidth;
    toastEl.classList.add("show");
    setTimeout(() => toastEl.classList.remove("show"), 2000);
}

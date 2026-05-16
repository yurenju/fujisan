// Minimal i18n: three locales (zh-Hant, en, ja), browser-language default,
// localStorage override. Strings are applied to elements with [data-i18n].

const STORAGE_KEY = 'fujisan.lang';
const SUPPORTED = ['zh', 'en', 'ja'];
const DEFAULT_LANG = 'zh';

const dict = {
  zh: {
    title: '富士山',
    subtitle: '日落的位移',
    lede: '去年秋天隱隱約約看到輪廓後，才知道從居所出門時正好看得到富士山。也因此才重新感知到地球傾斜角度對於日落位置的影響，特別是有了這座山作為標的物後，所有拍攝的照片就像是時光切片一樣，一層層的疊加在一起之後，就讓時間與季節流動運轉了起來。',
    desktopQr: '這個頁面需要傾斜手機來翻動照片，請用手機掃描下方 QR code 打開。',
    debugModeLabel: 'Debug mode',
    debugEnterBtn: '進入除錯模式',
    mobileInstruction: '請用拇指捏住紅圈處，輕輕的傾斜手機，翻動不同時間的富士山。放開拇指，照片就停下。',
    iosPermissionNote: 'iPhone 需要你授權動作感應，才能偵測手機的傾斜。按下下方按鈕後，畫面上會跳出系統提示，請選擇「允許」。',
    startBtn: '開始',
    startBtnIos: '允許動作感應並開始',
    permissionError: '沒有動作感應的權限就無法使用。請到 Safari 設定中重新允許，或重新整理頁面。',
    githubLink: '在 GitHub 查看原始碼',
  },
  en: {
    title: 'Fujisan',
    subtitle: 'The Drift of Sunset',
    lede: 'Last autumn, after vaguely making out its outline, I realized that Mount Fuji is visible just outside my home. Through this mountain, I re-perceived how the Earth\'s tilt shifts the position of sunset across the year. With Fuji as a fixed reference, every photograph became a slice of time — layered together, they let the seasons flow.',
    desktopQr: 'This page needs you to tilt a phone to flip through the photos. Please scan the QR code below with your phone to open it.',
    debugModeLabel: 'Debug mode',
    debugEnterBtn: 'Enter debug mode',
    mobileInstruction: 'Pinch the red circle with your thumb and gently tilt the phone to flip through Fuji across different moments. Let go, and the photo stops.',
    iosPermissionNote: 'iPhone requires permission to detect motion. When you tap the button below, a system prompt will appear — please choose "Allow".',
    startBtn: 'Start',
    startBtnIos: 'Allow motion & start',
    permissionError: 'Motion permission is required. Please re-enable it in Safari settings, or reload the page.',
    githubLink: 'View source on GitHub',
  },
  ja: {
    title: '富士山',
    subtitle: '夕日のずれ',
    lede: '昨秋、おぼろげな輪郭が見えてから、自宅を出るとちょうど富士山が見えることに気づきました。この山を目印にしたことで、地球の傾きが日没の位置に与える影響をあらためて感じ取れました。すべての写真は時間の切片のように重なり合い、時間と季節の流れを動かしていきます。',
    desktopQr: 'このページはスマートフォンを傾けて写真をめくる必要があります。下の QR コードをスマートフォンで読み取って開いてください。',
    debugModeLabel: 'Debug mode',
    debugEnterBtn: 'デバッグモードに入る',
    mobileInstruction: '親指で赤い丸をつまみ、スマートフォンをゆっくり傾けて、異なる時間の富士山をめくってください。指を離すと写真は止まります。',
    iosPermissionNote: 'iPhone ではモーションセンサーの許可が必要です。下のボタンを押すとシステムの確認が表示されるので「許可」を選んでください。',
    startBtn: 'スタート',
    startBtnIos: 'モーションを許可して開始',
    permissionError: 'モーションの権限がないと使用できません。Safari の設定で再度許可するか、ページを再読み込みしてください。',
    githubLink: 'GitHub でソースを見る',
  },
};

function detectDefault() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored && SUPPORTED.includes(stored)) return stored;
  const langs = navigator.languages?.length ? navigator.languages : [navigator.language || ''];
  for (const raw of langs) {
    const tag = raw.toLowerCase();
    if (tag.startsWith('ja')) return 'ja';
    if (tag.startsWith('zh')) return 'zh';
    if (tag.startsWith('en')) return 'en';
  }
  return DEFAULT_LANG;
}

let currentLang = detectDefault();
const listeners = new Set();

export function getLang() {
  return currentLang;
}

export function t(key) {
  return dict[currentLang]?.[key] ?? dict[DEFAULT_LANG][key] ?? key;
}

export function setLang(lang) {
  if (!SUPPORTED.includes(lang) || lang === currentLang) return;
  currentLang = lang;
  localStorage.setItem(STORAGE_KEY, lang);
  document.documentElement.lang = lang === 'zh' ? 'zh-Hant' : lang;
  applyDom();
  listeners.forEach(fn => fn(lang));
}

export function onLangChange(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function applyDom(root = document) {
  root.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });
  root.querySelectorAll('[data-i18n-aria-label]').forEach(el => {
    el.setAttribute('aria-label', t(el.dataset.i18nAriaLabel));
  });
}

export function initI18n() {
  document.documentElement.lang = currentLang === 'zh' ? 'zh-Hant' : currentLang;
  applyDom();
}

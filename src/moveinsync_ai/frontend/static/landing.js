const page = document.documentElement;
const dialog = document.querySelector('#login-dialog');
const status = document.querySelector('#form-status');
const result = document.querySelector('#scope-result');

document.querySelectorAll('[data-open-login]').forEach((button) => button.addEventListener('click', () => dialog.showModal()));
document.querySelectorAll('[data-close-login]').forEach((button) => button.addEventListener('click', () => dialog.close()));
dialog.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); });

document.querySelector('#theme-toggle').addEventListener('click', () => {
  page.dataset.theme = page.dataset.theme === 'dark' ? 'light' : 'dark';
});

document.querySelector('#menu-toggle').addEventListener('click', () => document.querySelector('#nav-links').classList.toggle('open'));

document.querySelector('#login-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  status.textContent = 'Checking your workspace access…';
  status.className = 'form-status';
  result.hidden = true;
  const form = new FormData(event.currentTarget);
  try {
    const login = await fetch('/auth/login', { method: 'POST', body: new URLSearchParams(form) });
    const token = await login.json();
    if (!login.ok) throw new Error(token.detail || 'Sign in failed.');
    const identity = await fetch('/auth/me', { headers: { Authorization: `Bearer ${token.access_token}` } });
    const user = await identity.json();
    if (!identity.ok) throw new Error(user.detail || 'Could not validate access.');
    sessionStorage.setItem('moveinsync_access_token', token.access_token);
    status.textContent = 'Signed in successfully.';
    status.className = 'form-status success';
    document.querySelector('#scope-name').textContent = user.user_type.replaceAll('_', ' ');
    document.querySelector('#scope-detail').textContent = user.access_scope === 'all_companies' ? 'Access: all companies' : `Access: company ID ${user.company_id}`;
    result.hidden = false;
  } catch (error) { status.textContent = error.message; }
});

document.querySelectorAll('.ripple').forEach((element) => element.addEventListener('pointerdown', (event) => {
  const ripple = document.createElement('span');
  ripple.className = 'ripple-dot';
  ripple.style.left = `${event.offsetX}px`;
  ripple.style.top = `${event.offsetY}px`;
  element.append(ripple);
  ripple.addEventListener('animationend', () => ripple.remove());
}));

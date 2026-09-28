document.addEventListener('DOMContentLoaded', function () {
    setupLikeButton();
    setupReadOnlyForms();
});

function setupLikeButton() {
    var likeBtn = document.getElementById('likeBtn');
    if (!likeBtn) {
        return;
    }

    var slug = likeBtn.getAttribute('data-article-slug');
    var storageKey = 'tsyoj-like:' + slug;
    var likeIcon = likeBtn.querySelector('.like-icon');
    var likeText = likeBtn.querySelector('.like-text');
    var likeCount = document.getElementById('likeCount');
    var baseCount = parseInt(likeCount.textContent, 10) || 0;
    var liked = readFlag(storageKey);

    function render() {
        likeBtn.classList.toggle('liked', liked);
        likeIcon.textContent = liked ? '\u2665' : '\u2661';
        likeText.textContent = liked ? 'Liked' : 'Like';
        likeCount.textContent = String(baseCount + (liked ? 1 : 0));
    }

    if (liked) {
        render();
    }

    likeBtn.addEventListener('click', function () {
        liked = !liked;
        writeFlag(storageKey, liked);
        render();
    });
}

function setupReadOnlyForms() {
    var forms = document.querySelectorAll('.comment-form, .subscribe-form, .login-box form');
    forms.forEach(function (form) {
        form.addEventListener('submit', function (event) {
            event.preventDefault();
            if (form.querySelector('.static-form-note')) {
                return;
            }

            var note = document.createElement('div');
            note.className = 'flash-message flash-error static-form-note';
            if (form.classList.contains('comment-form')) {
                note.textContent = 'New comments are added when the site is updated.';
            } else if (form.classList.contains('subscribe-form')) {
                note.textContent = 'Subscriptions are collected from the editing copy of the site.';
            } else {
                note.textContent = 'Admin sign-in is available on the editing copy of the site.';
            }
            form.insertBefore(note, form.firstChild);
        });
    });
}

function readFlag(key) {
    try {
        return localStorage.getItem(key) === '1';
    } catch (error) {
        return false;
    }
}

function writeFlag(key, value) {
    try {
        localStorage.setItem(key, value ? '1' : '0');
    } catch (error) {
        return;
    }
}

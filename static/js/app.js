$(document).ready(function () {

  /* ── Sidebar toggle (mobile) ─────────────────────────────────────────────── */
  $('#sidebarOpen').on('click', function () {
    $('#sidebar').addClass('open');
    $('#overlay').addClass('show');
  });

  function closeSidebar() {
    $('#sidebar').removeClass('open');
    $('#overlay').removeClass('show');
  }

  $('#sidebarClose, #overlay').on('click', closeSidebar);

  /* ── Global search with live dropdown ───────────────────────────────────── */
  let searchTimer;
  $('#global-search').on('input', function () {
    const q = $(this).val().trim();
    clearTimeout(searchTimer);
    if (q.length < 2) { $('#search-dropdown').hide().empty(); return; }
    searchTimer = setTimeout(function () {
      $.getJSON('/api/search', { q: q }, function (results) {
        const $dd = $('#search-dropdown').empty();
        if (results.length === 0) {
          $dd.html('<div class="sd-item"><span class="sd-title text-muted">No results found</span></div>').show();
          return;
        }
        results.forEach(function (r) {
          const avail = r.available > 0
            ? `<span class="sd-avail av-yes">${r.available} left</span>`
            : `<span class="sd-avail av-no">None</span>`;
          $dd.append(`
            <div class="sd-item" onclick="window.location='/book/${r.id}'">
              <div>
                <div class="sd-title">${r.title}</div>
                <div class="sd-author">${r.author} · ${r.genre}</div>
              </div>
              ${avail}
            </div>
          `);
        });
        $dd.show();
      });
    }, 280);
  });

  $(document).on('click', function (e) {
    if (!$(e.target).closest('.topbar-search').length) {
      $('#search-dropdown').hide();
    }
  });

  /* ── Auto-dismiss flash messages ────────────────────────────────────────── */
  setTimeout(function () {
    $('.flash-pill').fadeOut(400, function () { $(this).remove(); });
  }, 4500);

  /* ── Delete book modal ───────────────────────────────────────────────────── */
  window.confirmDel = function (id, title) {
    $('#del-title').text('"' + title + '"');
    $('#del-confirm').attr('href', '/delete_book/' + id);
    new bootstrap.Modal(document.getElementById('delModal')).show();
  };

  /* ── Add / Edit Book form validation ────────────────────────────────────── */
  $('#add-book-form, #edit-book-form').on('submit', function (e) {
    let ok = true;

    const title = $('#f-title').val().trim();
    if (!title) {
      fieldErr('#f-title', '#err-title', 'Book title is required.'); ok = false;
    } else if (title.length > 150) {
      fieldErr('#f-title', '#err-title', 'Title too long (max 150 chars).'); ok = false;
    } else {
      clearErr('#f-title', '#err-title');
    }

    const author = $('#f-author').val().trim();
    if (!author) {
      fieldErr('#f-author', '#err-author', 'Author name is required.'); ok = false;
    } else { clearErr('#f-author', '#err-author'); }

    const genre = $('#f-genre').val();
    if (!genre) {
      fieldErr('#f-genre', '#err-genre', 'Please select a genre.'); ok = false;
    } else { clearErr('#f-genre', '#err-genre'); }

    const copies = parseInt($('#f-copies').val(), 10);
    if (isNaN(copies) || copies < 1) {
      fieldErr('#f-copies', '#err-copies', 'At least 1 copy required.'); ok = false;
    } else { clearErr('#f-copies', '#err-copies'); }

    if (!ok) { e.preventDefault(); shake('.btn-submit'); }
  });

  /* ── Live card preview on Add Book page ─────────────────────────────────── */
  if ($('#preview-card').length) {
    function updatePreview() {
      const title  = $('#f-title').val().trim()  || 'Book Title';
      const author = $('#f-author').val().trim()  || 'Author Name';
      const genre  = $('#f-genre').val()          || 'Genre';
      const copies = parseInt($('#f-copies').val(), 10) || 1;
      const color  = $('input[name="cover_color"]:checked').val() || '#c8dfc8';

      $('#prev-title').text(title);
      $('#prev-author').text(author);
      $('#prev-genre').text(genre);
      $('#prev-avail').text(copies + ' left');
      $('#preview-card').css('--spine', color);
      $('.bc-spine').css('background', color);
    }

    $('#f-title, #f-author, #f-genre, #f-copies').on('input change', updatePreview);
    $('input[name="cover_color"]').on('change', updatePreview);
    updatePreview();
  }

  /* ── Borrow form validation & live summary ──────────────────────────────── */
  if ($('#borrow-form').length) {
    // Set min date
    const tmr = new Date(); tmr.setDate(tmr.getDate() + 1);
    $('#b-due').attr('min', tmr.toISOString().split('T')[0]);

    // Duration shortcuts
    $('.ds-btn').on('click', function () {
      const days = parseInt($(this).data('days'), 10);
      const d = new Date(); d.setDate(d.getDate() + days);
      const iso = d.toISOString().split('T')[0];
      $('#b-due').val(iso);
      updateIssueSummary();
      $('.ds-btn').removeClass('ds-active');
      $(this).addClass('ds-active');
    });

    // Member auto-fill
    $('#member-select').on('change', function () {
      const $opt = $(this).find(':selected');
      if ($opt.val()) {
        $('#b-name').val($opt.data('name'));
        $('#b-email').val($opt.data('email'));
        $('#b-phone').val($opt.data('phone'));
        updateIssueSummary();
      }
    });

    function updateIssueSummary() {
      const name  = $('#b-name').val() || '—';
      const email = $('#b-email').val() || '—';
      const due   = $('#b-due').val();
      let daysStr = '—';
      if (due) {
        const diff = Math.ceil((new Date(due) - new Date()) / 86400000);
        daysStr = diff > 0 ? diff + ' days from today' : 'Invalid date';
      }
      $('#sum-name').text(name);
      $('#sum-email').text(email);
      $('#sum-due').text(due || '—');
      $('#sum-days').text(daysStr);
    }

    $('#b-name, #b-email, #b-due').on('input change', updateIssueSummary);

    // Email live check
    $('#b-email').on('blur', function () {
      const rx = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if ($(this).val() && !rx.test($(this).val())) {
        fieldErr('#b-email', '#err-email', 'Invalid email format.');
      } else { clearErr('#b-email', '#err-email'); }
    });

    // Submit validation
    $('#borrow-form').on('submit', function (e) {
      let ok = true;
      const name = $('#b-name').val().trim();
      if (!name) { fieldErr('#b-name', '#err-name', 'Name is required.'); ok = false; }
      else { clearErr('#b-name', '#err-name'); }

      const email = $('#b-email').val().trim();
      if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        fieldErr('#b-email', '#err-email', 'Valid email is required.'); ok = false;
      } else { clearErr('#b-email', '#err-email'); }

      const due = $('#b-due').val();
      const today = new Date().toISOString().split('T')[0];
      if (!due) { fieldErr('#b-due', '#err-due', 'Due date is required.'); ok = false; }
      else if (due <= today) { fieldErr('#b-due', '#err-due', 'Due date must be future.'); ok = false; }
      else { clearErr('#b-due', '#err-due'); }

      if (!ok) { e.preventDefault(); shake('.btn-submit'); }
    });
  }

  /* ── Member registration form ───────────────────────────────────────────── */
  if ($('#member-form').length) {
    // Password strength
    $('#m-password').on('input', function () {
      const v = $(this).val();
      let str = 0;
      if (v.length >= 6) str++;
      if (v.length >= 10) str++;
      if (/[A-Z]/.test(v)) str++;
      if (/[0-9]/.test(v)) str++;
      if (/[^A-Za-z0-9]/.test(v)) str++;
      const colors = ['', '#dc2626', '#f59e0b', '#3b82f6', '#22c55e', '#16a34a'];
      const widths = ['0%', '20%', '40%', '65%', '85%', '100%'];
      $('#pw-bar').css({ width: widths[str] || '0%', background: colors[str] || 'transparent' });
    });

    // Show/hide password
    $('#pw-toggle').on('click', function () {
      const $input = $('#m-password');
      const type = $input.attr('type') === 'password' ? 'text' : 'password';
      $input.attr('type', type);
      $(this).find('i').toggleClass('bi-eye bi-eye-slash');
    });

    // Submit validation
    $('#member-form').on('submit', function (e) {
      let ok = true;
      const name = $('#m-name').val().trim();
      if (!name) { fieldErr('#m-name', '#err-mname', 'Name is required.'); ok = false; }
      else { clearErr('#m-name', '#err-mname'); }

      const email = $('#m-email').val().trim();
      if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        fieldErr('#m-email', '#err-memail', 'Valid email is required.'); ok = false;
      } else { clearErr('#m-email', '#err-memail'); }

      const pwd = $('#m-password').val();
      if (pwd.length < 6) {
        fieldErr('#m-password', '#err-mpwd', 'Password must be 6+ characters.'); ok = false;
      } else { clearErr('#m-password', '#err-mpwd'); }

      if (!ok) { e.preventDefault(); shake('.btn-submit'); }
    });
  }

  /* ── Animate genre bars on reports page ─────────────────────────────────── */
  if ($('.gb-bar').length) {
    $('.gb-bar').each(function () {
      const target = $(this).css('width');
      $(this).css('width', '0').animate({ width: target }, 700);
    });
  }

  /* ── Helpers ─────────────────────────────────────────────────────────────── */
  function fieldErr(sel, errSel, msg) {
    $(sel).addClass('is-invalid');
    $(errSel).text(msg);
  }

  function clearErr(sel, errSel) {
    $(sel).removeClass('is-invalid');
    $(errSel).text('');
  }

  function shake(sel) {
    $(sel).addClass('shake');
    setTimeout(() => $(sel).removeClass('shake'), 500);
  }
});

// Shake keyframe
const s = document.createElement('style');
s.textContent = `
  .shake { animation: shake .4s ease; }
  @keyframes shake {
    0%,100%{transform:translateX(0)} 20%{transform:translateX(-6px)}
    40%{transform:translateX(6px)}   60%{transform:translateX(-4px)} 80%{transform:translateX(4px)}
  }
  .ds-active { border-color: var(--sage) !important; color: var(--sage) !important; background: var(--sage-lt) !important; }
`;
document.head.appendChild(s);

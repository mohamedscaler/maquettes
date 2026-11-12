/* Maquette épaviste — scripts communs */
(function () {
  var WA = '33766305938';
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.documentElement.classList.add('js');

  /* --- Menu mobile --- */
  var toggle = document.querySelector('.navbar_toggle');
  var menu = document.querySelector('.navbar_menu');
  function setMenu(open) {
    menu.classList.toggle('is-open', open);
    toggle.setAttribute('aria-expanded', open);
    toggle.setAttribute('aria-label', open ? 'Fermer le menu' : 'Ouvrir le menu');
  }
  if (toggle && menu) {
    toggle.addEventListener('click', function () { setMenu(!menu.classList.contains('is-open')); });
    menu.addEventListener('click', function (e) { if (e.target.closest('a')) setMenu(false); });
  }

  /* --- Ombre sous la barre quand on défile --- */
  var nav = document.querySelector('.navbar_component');
  function onScroll() { if (nav) nav.classList.toggle('is-scrolled', window.scrollY > 80); }
  window.addEventListener('scroll', onScroll, { passive: true }); onScroll();

  /* --- Défilements infinis : on duplique le contenu pour une boucle sans coupure --- */
  document.querySelectorAll('[data-marquee]').forEach(function (el) {
    el.innerHTML += el.innerHTML;
    el.querySelectorAll(':scope > *').forEach(function (c, i, all) { if (i >= all.length / 2) c.setAttribute('aria-hidden', 'true'); });
  });

  /* --- Apparitions au scroll, en cascade par groupe --- */
  document.querySelectorAll('[data-reveal-group]').forEach(function (g) {
    g.querySelectorAll('[data-reveal]').forEach(function (el, i) { el.style.setProperty('--delay', Math.min(i * 0.08, 0.64) + 's'); });
  });
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target); } });
  }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
  document.querySelectorAll('[data-reveal], .steps_grid').forEach(function (el) { io.observe(el); });

  /* --- Vidéo du hero : coupée si l'utilisateur réduit les animations --- */
  var video = document.querySelector('.hero_media video');
  if (video && reduce) { video.removeAttribute('autoplay'); video.pause(); }

  /* --- Outil « Vos papiers » --- */
  var tool = document.querySelector('[data-papers]');
  if (tool) {
    var panels = tool.querySelectorAll('.papers_panel');
    panels.forEach(function (p, i) { p.hidden = i !== 0; }); // sans JS, tout reste visible
    tool.addEventListener('change', function (e) {
      if (!e.target.matches('input[name="situation"]')) return;
      panels.forEach(function (p) {
        var on = p.dataset.panel === e.target.value;
        p.hidden = !on;
        if (on && !reduce) { p.classList.remove('is-in'); void p.offsetWidth; p.classList.add('is-in'); }
      });
    });
  }

  /* --- Bouton « Être rappelé » : descend au formulaire et place le curseur sur le nom --- */
  document.querySelectorAll('[data-goto-form]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      var form = document.querySelector('#demande');
      if (!form) return;
      e.preventDefault();
      form.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
      var first = form.querySelector('input');
      if (first) setTimeout(function () { first.focus({ preventScroll: true }); }, reduce ? 0 : 600);
    });
  });

  /* --- Formulaires → demande envoyée par e-mail (FormSubmit) --- */
  var MAIL = ''; // maquette : pas d'envoi réel
  document.querySelectorAll('[data-mail-form]').forEach(function (form) {
    var status = form.querySelector('[data-form-status]');
    var btn = form.querySelector('button[type="submit"]');
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      // Vérification des champs obligatoires
      var ok = true;
      form.querySelectorAll('[required]').forEach(function (f) {
        var err = form.querySelector('[data-error-for="' + f.name + '"]');
        var bad = !f.value.trim() || (f.type === 'tel' && f.value.replace(/\D/g, '').length < 10);
        if (err) err.textContent = bad ? (f.type === 'tel' ? 'Indiquez un numéro à 10 chiffres.' : 'Ce champ est nécessaire.') : '';
        f.setAttribute('aria-invalid', bad);
        if (bad && ok) { f.focus(); ok = false; }
      });
      if (!ok || form.classList.contains('is-sending')) return;
      if (!MAIL) { form.classList.add('is-sent'); form.innerHTML = '<div class="form_success"><p class="form_success_title">Demande envoyée ✓</p><p>Démo de la maquette : sur le site final, cette demande arrive directement chez Epaviste Toulouse 31.</p></div>'; return; }
      // Données envoyées avec les intitulés lisibles (comme l'ancien site)
      var data = { _subject: "Nouvelle demande depuis le site", _template: 'table', _captcha: 'false', Page: location.pathname };
      new FormData(form).forEach(function (v, k) {
        var field = form.querySelector('[name="' + k + '"]');
        if (k === '_honey') { data._honey = v; return; }
        if (String(v).trim()) data[(field && field.dataset.label) || k] = v;
      });
      if (data.Email) data._replyto = data.Email;
      form.classList.add('is-sending'); btn.disabled = true;
      fetch(MAIL, { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify(data) })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(function (res) {
          // FormSubmit répond 200 même si l'envoi a échoué (formulaire non activé…) : on vérifie le champ success
          if (!res || String(res.success) !== 'true') throw new Error((res && res.message) || 'envoi refusé');
          track('Lead', 'formulaire');
          form.classList.add('is-sent');
          form.innerHTML = '<div class="form_success"><p class="form_success_title">Demande envoyée ✓</p><p>Merci, on vous rappelle très vite au numéro indiqué.</p><p>Urgent ? Appelez le <a href="tel:+33766305938">07 66 30 59 38</a></p></div>';
        })
        .catch(function () {
          form.classList.remove('is-sending'); btn.disabled = false;
          status.innerHTML = "Envoi impossible pour le moment. Appelez le <a href=\"tel:+33766305938\">07 66 30 59 38</a> ou <a href=\"https://wa.me/" + WA + "\" target=\"_blank\" rel=\"noopener\">écrivez-nous sur WhatsApp</a>.";
          status.classList.add('is-error');
        });
    });
  });

  /* --- Suivi Ads : appels, WhatsApp, formulaires (Google Ads / GTM / Meta Pixel s'ils sont installés) --- */
  var ADS = {};
  function track(name, label) {
    if (window.gtag && ADS[label]) window.gtag('event', 'conversion', { send_to: ADS[label] });
    if (window.dataLayer) window.dataLayer.push({ event: 'contact_click', contact_type: label });
    if (window.fbq) window.fbq('track', name === 'Lead' ? 'Lead' : 'Contact', { method: label });
  }
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a[href^="tel:"], a[href*="wa.me"]');
    if (a) track('Contact', a.href.indexOf('tel:') === 0 ? 'appel' : 'whatsapp');
  });
})();

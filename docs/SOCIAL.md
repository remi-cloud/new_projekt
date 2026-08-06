# Social desk — news → X / LinkedIn

News agent składa posty z makro-newsów. **Domyślnie dry-run**: zapis w DB + podgląd w UI (`/news`), **bez wysyłki**.

## Szybki start (lokalnie / Docker)

1. Skopiuj zmienne z `.env.example` do `.env`.
2. Zostaw:
   ```
   CYCLICAL_SOCIAL_ENABLED=true
   CYCLICAL_SOCIAL_DRY_RUN=true
   CYCLICAL_SOCIAL_AUTO_POST=false
   ```
3. Odśwież newsy (`POST /api/news/macro/refresh` lub przycisk na `/news`).
4. Sprawdź `GET /api/social/posts` albo sekcję **Social desk** na `/news`.

## X (Twitter)

1. Wejdź na [developer.x.com](https://developer.x.com) → utwórz Project + App.
2. App permissions: **Read and Write**.
3. Keys and tokens → wygeneruj:
   - API Key + API Secret
   - Access Token + Access Token Secret (OAuth 1.0a)
4. Wklej do `.env`:
   ```
   CYCLICAL_X_API_KEY=...
   CYCLICAL_X_API_SECRET=...
   CYCLICAL_X_ACCESS_TOKEN=...
   CYCLICAL_X_ACCESS_TOKEN_SECRET=...
   ```

## LinkedIn

1. [LinkedIn Developers](https://www.linkedin.com/developers/) → Create app.
2. Podłącz produkt z uprawnieniem share (np. **Share on LinkedIn** / Community Management API).
3. Uzyskaj access token z scope `w_member_social` (profil) lub `w_organization_social` (strona firmowa).
4. Author URN:
   - osoba: `urn:li:person:XXXX`
   - strona KAR Digital: `urn:li:organization:XXXX`
5. Wklej:
   ```
   CYCLICAL_LINKEDIN_ACCESS_TOKEN=...
   CYCLICAL_LINKEDIN_AUTHOR_URN=urn:li:organization:...
   ```

## Publiczny link w poście

```
# Preferowana domena PH — patrz docs/DOMAIN-PH.md
CYCLICAL_PUBLIC_BASE_URL=https://kardigital.ph
```

W stopce postu pojawi się `{PUBLIC_BASE_URL}/news` (albo URL artykułu).  
Nie wstawiaj tu `*.trycloudflare.com` — URL się zmienia przy każdym quick tunnelu.

## Przejście dry-run → live

1. Uzupełnij tokeny X i/lub LinkedIn.
2. W UI: **Publikuj** na wybranym poście (`POST /api/social/posts/{id}/publish`) — wymusza wysyłkę nawet przy dry-run (jednorazowo).
3. Gdy OK:
   ```
   CYCLICAL_SOCIAL_DRY_RUN=false
   CYCLICAL_SOCIAL_AUTO_POST=true
   ```
4. Restart kontenera / procesu.

## Status API

- `GET /api/social/status` — enabled, dry_run, auto_post, x_configured, linkedin_configured
- `GET /api/social/posts` — ostatnie posty
- `POST /api/social/posts/{id}/publish` — ręczna publikacja

## Limity

- `CYCLICAL_SOCIAL_MAX_PER_CYCLE` (domyślnie 2 newsy × 2 platformy na cykl)
- `CYCLICAL_SOCIAL_COOLDOWN_MINUTES` między postami na platformę
- Dedupe: ten sam URL/news nie idzie drugi raz na tę samą platformę

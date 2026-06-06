import { expect, test } from '@playwright/test'

const phasesForTurn = [
  'Resume Validation',
  'Resume Validation',
  'Technical Assessment',
  'Technical Assessment',
  'Technical Assessment',
  'Technical Assessment',
  'Technical Assessment',
  'Behavioral Assessment',
  'Behavioral Assessment',
  'Behavioral Assessment',
  'Final Evaluation',
  'Final Evaluation',
]

const makeJwt = () => {
  const payload = {
    sub: 42,
    username: 'candidate_e2e',
    role: 'candidate',
    exp: Math.floor(Date.now() / 1000) + 3600,
  }
  const encoded = Buffer.from(JSON.stringify(payload)).toString('base64url')
  return `e2e.${encoded}.signature`
}

const installAuth = async (page) => {
  await page.addInitScript((token) => {
    window.localStorage.setItem('tf_token', token)
    window.localStorage.setItem('tf_has_resume', 'true')
  }, makeJwt())
}

const installBrowserMedia = async (page) => {
  await page.addInitScript(() => {
    window.__tfE2E = {
      events: [],
      denyCamera: false,
      denyMicrophone: false,
      denyScreen: false,
      screenInterrupted: false,
      fullscreen: false,
    }

    const pushEvent = (type, payload = {}) => {
      window.__tfE2E.events.push({ type, payload, at: Date.now() })
      console.info(`e2e_${type}`, payload)
    }

    const makeTrack = (kind) => ({
      kind,
      label: `E2E ${kind}`,
      enabled: true,
      muted: false,
      readyState: 'live',
      getSettings: () => kind === 'video' ? { displaySurface: 'monitor', width: 1280, height: 720 } : { sampleRate: 48000, channelCount: 1 },
      stop() {
        this.readyState = 'ended'
        if (typeof this.onended === 'function') this.onended()
      },
      onended: null,
      onmute: null,
      onunmute: null,
    })

    const makeStream = (kind) => {
      const track = makeTrack(kind)
      return {
        id: `e2e-${kind}-${Date.now()}`,
        getTracks: () => [track],
        getAudioTracks: () => kind === 'audio' ? [track] : [],
        getVideoTracks: () => kind === 'video' ? [track] : [],
      }
    }

    Object.defineProperty(HTMLMediaElement.prototype, 'srcObject', {
      configurable: true,
      get() {
        return this.__tfSrcObject || null
      },
      set(value) {
        this.__tfSrcObject = value
      },
    })

    window.AudioContext = undefined
    window.webkitAudioContext = undefined

    Object.defineProperty(window.navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: async (constraints) => {
          pushEvent('media_get_user_media', { constraints })
          if (constraints?.audio && window.__tfE2E.denyMicrophone) {
            throw Object.assign(new Error('Microphone denied'), { name: 'NotAllowedError' })
          }
          if (constraints?.video && window.__tfE2E.denyCamera) {
            throw Object.assign(new Error('Camera denied'), { name: 'NotAllowedError' })
          }
          return makeStream(constraints?.audio ? 'audio' : 'video')
        },
        getDisplayMedia: async () => {
          pushEvent('media_get_display_media')
          if (window.__tfE2E.denyScreen) {
            throw Object.assign(new Error('Screen share denied'), { name: 'NotAllowedError' })
          }
          const stream = makeStream('video')
          window.__tfE2E.lastScreenTrack = stream.getVideoTracks()[0]
          return stream
        },
      },
    })

    Object.defineProperty(document, 'fullscreenElement', {
      configurable: true,
      get: () => window.__tfE2E.fullscreen ? document.documentElement : null,
    })
    Element.prototype.requestFullscreen = async function requestFullscreen() {
      window.__tfE2E.fullscreen = true
      pushEvent('fullscreen_enter')
      document.dispatchEvent(new Event('fullscreenchange'))
    }
    document.exitFullscreen = async () => {
      window.__tfE2E.fullscreen = false
      pushEvent('fullscreen_exit')
      document.dispatchEvent(new Event('fullscreenchange'))
    }

    class FakeMediaRecorder {
      constructor(stream) {
        this.stream = stream
        this.state = 'inactive'
        this.mimeType = 'audio/webm'
        this.audioBitsPerSecond = 128000
        this.ondataavailable = null
        this.onstop = null
        this.onerror = null
      }

      static isTypeSupported() {
        return true
      }

      start(timeslice) {
        this.state = 'recording'
        pushEvent('recorder_start', { timeslice })
      }

      stop() {
        if (this.state === 'inactive') return
        this.state = 'inactive'
        pushEvent('recorder_stop')
        const blob = new Blob([new Uint8Array(48_000)], { type: this.mimeType })
        if (this.ondataavailable) this.ondataavailable({ data: blob })
        if (this.onstop) this.onstop()
      }
    }

    window.MediaRecorder = FakeMediaRecorder
  })
}

const installInterviewApi = async (page, options = {}) => {
  const state = {
    answers: 0,
    transcriptAttempts: 0,
    events: [],
    messages: [
      {
        role: 'ai',
        content: 'Tell me about yourself as it relates to this Backend Engineer role.',
        phase: 'Resume Validation',
        timestamp: new Date().toISOString(),
      },
    ],
  }

  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname
    const method = request.method()

    if (!path.startsWith('/api/')) {
      return route.continue()
    }

    state.events.push({ method, path })

    if (path === '/api/interview/start-for-application' && method === 'POST') {
      const phase = phasesForTurn[Math.max(0, state.answers - 1)] || 'Resume Validation'
      const lastQuestion = [...state.messages].reverse().find((m) => m.role === 'ai')?.content
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session_id: 'session-e2e',
          db_id: 77,
          role: 'Backend Engineer',
          status: 'active',
          question: lastQuestion,
          phase,
          phase_goal: 'Validate interview browser flow.',
          interviewer_persona: 'balanced',
          messages: state.messages,
        }),
      })
    }

    if (path === '/api/interview/transcribe' && method === 'POST') {
      state.transcriptAttempts += 1
      const body = request.postData() || ''
      const requestId = body.match(/(\d+-\d+-\d+)/)?.[1] || `request-${state.transcriptAttempts}`
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          transcript: `E2E transcript answer ${state.transcriptAttempts}`,
          confidence: 0.98,
          duration: 5,
          processing_time_ms: 35,
          model: 'e2e-whisper',
          language: 'en',
          request_id: requestId,
        }),
      })
    }

    if (path === '/api/interview/answer' && method === 'POST') {
      const payload = JSON.parse(request.postData() || '{}')
      state.answers += 1
      const phase = phasesForTurn[state.answers - 1] || 'Final Evaluation'
      const complete = state.answers >= (options.turnsToComplete || 12)
      state.messages.push({ role: 'user', content: payload.answer, timestamp: new Date().toISOString() })
      if (!complete) {
        state.messages.push({
          role: 'ai',
          content: `Question ${state.answers + 1} for ${phasesForTurn[state.answers]}`,
          phase: phasesForTurn[state.answers],
          timestamp: new Date().toISOString(),
        })
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          next_question: complete ? '' : `Question ${state.answers + 1} for ${phasesForTurn[state.answers]}`,
          phase,
          phase_goal: `Goal for ${phase}`,
          status: complete ? 'analyzing' : 'active',
          interview_complete: complete,
          session_turn: state.answers,
          messages: state.messages,
          db_id: 77,
        }),
      })
    }

    if (path === '/api/interview/sessions/77' && method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 77,
          session_token: 'session-e2e',
          role: 'Backend Engineer',
          status: 'analyzed',
          messages: state.messages,
        }),
      })
    }

    if (path === '/api/interview/session-e2e/violation' && method === 'POST') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, cancelled: false, violations_count: 1 }),
      })
    }

    if (path === '/api/interview/session-e2e/abandon' && method === 'POST') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'cancelled' }),
      })
    }

    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true, applications: [] }),
    })
  })

  return state
}

const bootInterview = async (page, apiOptions) => {
  const pageErrors = []
  page.on('pageerror', (error) => pageErrors.push(error.message))
  page.on('console', (message) => {
    if (message.type() === 'error') pageErrors.push(message.text())
  })
  await installAuth(page)
  await installBrowserMedia(page)
  const apiState = await installInterviewApi(page, apiOptions)
  await page.goto('/interview?appId=101')
  await expect.poll(async () => {
    if (pageErrors.length) return pageErrors.join('\n')
    return await page.locator('body').innerText().catch(() => '')
  }, { timeout: 8_000 }).toContain('Backend Engineer Interview')
  await expect(page.getByRole('heading', { name: /Backend Engineer Interview/i })).toBeVisible()
  return apiState
}

const completeProctoring = async (page) => {
  await page.getByRole('button', { name: /Start Proctored Interview/i }).click()
  await expect(page.getByText(/Proctoring: Active/i)).toBeVisible()
  await expect(page.getByText(/Feed Active/i)).toBeVisible()
  await expect(page.getByText(/Screen Share Status/i)).toBeVisible()
}

const answerByVoice = async (page) => {
  await page.getByRole('button', { name: /Start Voice Recording/i }).click()
  await expect(page.getByText(/Recording Speech/i)).toBeVisible()
  await page.getByRole('button', { name: /Stop Recording/i }).click()
  await expect(page.getByText(/Review Speech Transcript/i)).toBeVisible()
  const transcript = page.getByRole('textbox')
  await expect(transcript).toHaveValue(/E2E transcript answer/)
  await page.getByRole('button', { name: /Use & Submit/i }).click()
}

test.describe('TalentForge interview browser validation', () => {
  test('candidate completes full interview with proctoring, recording, transcription, phase progression, and report handoff', async ({ page }) => {
    const apiState = await bootInterview(page)

    const sidebar = page.locator('aside')
    await expect(sidebar).toBeVisible()
    await completeProctoring(page)

    await expect(page.locator('main')).toHaveJSProperty('scrollTop', 0)
    await expect(page.getByText(/Tell me about yourself/i)).toBeVisible()

    for (let turn = 1; turn <= 12; turn += 1) {
      await answerByVoice(page)
      if (turn === 3) {
        await expect(page.getByText(/Phase: Technical Assessment \| Proctoring: Active/i)).toBeVisible()
      }
      if (turn === 8) {
        await expect(page.getByText(/Phase: Behavioral Assessment \| Proctoring: Active/i)).toBeVisible()
      }
      if (turn === 11) {
        await expect(page.getByText(/Phase: Final Evaluation \| Proctoring: Active/i)).toBeVisible()
      }
    }

    await expect(page.getByText(/Interview completed\. Generating final report/i)).toBeVisible()
    await expect.poll(() => apiState.answers).toBe(12)

    const diagnostics = await page.evaluate(() => window.__tfE2E.events.map((event) => event.type))
    expect(diagnostics).toContain('media_get_user_media')
    expect(diagnostics).toContain('media_get_display_media')
    expect(diagnostics).toContain('fullscreen_enter')
    expect(diagnostics).toContain('recorder_start')
    expect(diagnostics).toContain('recorder_stop')
  })

  test('refresh during interview resumes active state without breaking layout or sidebar', async ({ page }) => {
    const apiState = await bootInterview(page)
    await completeProctoring(page)
    await answerByVoice(page)

    await page.reload()
    await expect(page.locator('aside')).toBeVisible()
    await expect(page.getByText(/Question 2 for Resume Validation/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /Start Proctored Interview/i })).toBeVisible()
    expect(apiState.answers).toBe(1)
  })

  test('cancel recording and re-record keeps only the latest transcript path active', async ({ page }) => {
    await bootInterview(page)
    await completeProctoring(page)

    await page.getByRole('button', { name: /Start Voice Recording/i }).click()
    await page.getByRole('button', { name: /Stop Recording/i }).click()
    await expect(page.getByText(/Review Speech Transcript/i)).toBeVisible()
    await page.getByRole('button', { name: /Re-record/i }).click()
    await expect(page.getByRole('button', { name: /Start Voice Recording/i })).toBeVisible()

    await answerByVoice(page)
    await expect(page.getByText(/Question 2 for Resume Validation/i)).toBeVisible()
  })

  test('permission denial falls back safely without a stuck proctoring modal or recorder state', async ({ page }) => {
    await bootInterview(page)

    await page.evaluate(() => {
      window.__tfE2E.denyCamera = true
      window.__tfE2E.denyScreen = true
    })
    await page.getByRole('button', { name: /Start Proctored Interview/i }).click()
    await expect(page.getByText(/Camera, screen sharing, and browser fullscreen are all required/i)).toBeVisible()
    await expect(page.getByRole('heading', { name: /Proctoring setup required/i })).toBeVisible()

    await page.evaluate(() => {
      window.__tfE2E.denyCamera = false
      window.__tfE2E.denyScreen = false
    })
    await completeProctoring(page)

    await page.evaluate(() => {
      window.__tfE2E.denyMicrophone = true
    })
    await page.getByRole('button', { name: /Start Voice Recording/i }).click()
    await expect(page.getByRole('textbox')).toBeVisible()
    await expect(page.getByRole('button', { name: /Submit Answer/i })).toBeVisible()
  })

  test('screen-share interruption reopens setup state and logs a proctoring alert', async ({ page }) => {
    await bootInterview(page)
    await completeProctoring(page)

    await page.evaluate(() => {
      window.__tfE2E.lastScreenTrack.stop()
    })

    await expect(page.getByRole('button', { name: /Start Proctored Interview/i })).toBeVisible()
    await expect(page.getByText('Screen sharing', { exact: true })).toBeVisible()
  })
})

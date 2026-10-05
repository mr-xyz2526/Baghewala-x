import React, { useState, useEffect } from 'react'
import { NavBar } from './components/NavBar'
import { FieldPage } from './pages/FieldPage'
import { WellTwinPage } from './pages/WellTwinPage'
import { CSSPage } from './pages/CSSPage'
import { SRPPage } from './pages/SRPPage'
import { OptimizePage } from './pages/OptimizePage'
import { RiskPage } from './pages/RiskPage'
import { WhatIfPage } from './pages/WhatIfPage'
import { HistoryPage } from './pages/HistoryPage'
import { api } from './api/client'
import type { TwinRunResult } from './types'

export type NavScreen = 'field' | 'twin' | 'css' | 'srp' | 'optimize' | 'risk' | 'whatif' | 'history'

export type TwinMode = 'SIMULATION_MODE' | 'SYNCHRONIZED'

const DEMO_DEFAULTS = {
  well_id: 'BW-101',
  well_name: 'Baghewala BW-101',
  field_name: 'Baghewala Field',
  steam_rate_tpd: 800,
  steam_temp_c: 260,
  injection_days: 18,
  steam_quality: 0.8,
  soak_days: 4,
  production_days: 70,
  spm: 6.0,
  vfd_hz: 36.0,
  water_cut_pct: 30,
  oil_price_usd_bbl: 60,
  steam_cost_usd_tonne: 12,
}

export default function App() {
  const [screen, setScreen] = useState<NavScreen>('field')
  const [twinMode, setTwinMode] = useState<TwinMode>('SIMULATION_MODE')
  const [twinResult, setTwinResult] = useState<TwinRunResult | null>(null)
  const [twinLoading, setTwinLoading] = useState(false)
  const [twinParams, setTwinParams] = useState(DEMO_DEFAULTS)
  const [backendOk, setBackendOk] = useState<boolean | null>(null)

  // Check backend on mount
  useEffect(() => {
    api.health()
      .then(() => {
        setBackendOk(true)
        setTwinMode('SYNCHRONIZED')
      })
      .catch(() => setBackendOk(false))
  }, [])

  const runTwin = async (params = twinParams) => {
    setTwinLoading(true)
    try {
      const res = await api.twin.run(params)
      setTwinResult(res)
      setTwinParams(params)
      setTwinMode('SYNCHRONIZED')
    } catch (e) {
      console.error('Twin run failed', e)
      setTwinMode('SIMULATION_MODE')
    } finally {
      setTwinLoading(false)
    }
  }

  const sharedProps = {
    twinResult,
    twinLoading,
    twinParams,
    setTwinParams,
    runTwin,
    setScreen,
  }

  return (
    <div className="shell">
      <NavBar
        screen={screen}
        onNavigate={setScreen}
        twinMode={twinMode}
        backendOk={backendOk}
        twinLoading={twinLoading}
      />

      <main className="page-content">
        {screen === 'field'    && <FieldPage    {...sharedProps} />}
        {screen === 'twin'     && <WellTwinPage {...sharedProps} />}
        {screen === 'css'      && <CSSPage      {...sharedProps} />}
        {screen === 'srp'      && <SRPPage      {...sharedProps} />}
        {screen === 'optimize' && <OptimizePage {...sharedProps} />}
        {screen === 'risk'     && <RiskPage     {...sharedProps} />}
        {screen === 'whatif'   && <WhatIfPage   {...sharedProps} />}
        {screen === 'history'  && <HistoryPage  {...sharedProps} />}
      </main>
    </div>
  )
}

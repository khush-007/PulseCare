import { useState } from 'react';
import { ChatWidget } from './features/chatbot';

export default function App() {
  const [activeTab, setActiveTab] = useState<'home' | 'doctors' | 'services' | 'triage'>('home');
  const [authToken, setAuthToken] = useState<string | undefined>();
  const [currentUser, setCurrentUser] = useState<string | null>(null);

  // Quick Demo Login helper to showcase authenticated chatbot tools
  const handleQuickLogin = async (email: string) => {
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password: 'patient123' }),
      });
      if (res.ok) {
        const data = await res.json();
        setAuthToken(data.access_token);
        setCurrentUser(data.full_name);
      }
    } catch (e) {
      console.error('Quick login failed:', e);
    }
  };

  const handleLogout = () => {
    setAuthToken(undefined);
    setCurrentUser(null);
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans">
      {/* Navigation Bar */}
      <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-slate-200 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-teal-700 to-cyan-500 flex items-center justify-center text-white font-bold text-lg shadow-md shadow-teal-500/20">
              ❤️
            </div>
            <div>
              <span className="text-xl font-bold tracking-tight text-slate-900">
                Pulse<span className="text-teal-600">Care</span>
              </span>
              <span className="hidden sm:inline-block ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-teal-50 text-teal-700 border border-teal-200">
                Smart Healthcare System
              </span>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-600">
            <button
              onClick={() => setActiveTab('home')}
              className={`hover:text-teal-600 transition ${activeTab === 'home' ? 'text-teal-600 font-semibold' : ''}`}
            >
              Overview
            </button>
            <button
              onClick={() => setActiveTab('doctors')}
              className={`hover:text-teal-600 transition ${activeTab === 'doctors' ? 'text-teal-600 font-semibold' : ''}`}
            >
              Specialists & Doctors
            </button>
            <button
              onClick={() => setActiveTab('services')}
              className={`hover:text-teal-600 transition ${activeTab === 'services' ? 'text-teal-600 font-semibold' : ''}`}
            >
              Medical Services
            </button>
            <button
              onClick={() => setActiveTab('triage')}
              className={`hover:text-teal-600 transition ${activeTab === 'triage' ? 'text-teal-600 font-semibold' : ''}`}
            >
              AI Clinical Triage
            </button>
          </nav>

          <div className="flex items-center gap-3">
            {currentUser ? (
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-slate-700 bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200">
                  👤 {currentUser}
                </span>
                <button
                  onClick={handleLogout}
                  className="text-xs px-2.5 py-1.5 text-slate-500 hover:text-slate-800 font-medium"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleQuickLogin('john.doe@example.com')}
                  className="text-xs font-medium text-teal-700 hover:text-teal-800 bg-teal-50 hover:bg-teal-100/70 border border-teal-200 px-3 py-1.5 rounded-lg transition"
                  title="Demo login as patient John Doe to test personalized appointment queries"
                >
                  Demo Sign-In (John Doe)
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full space-y-12">
        {/* Hero Section */}
        <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 via-teal-950 to-slate-900 text-white p-8 sm:p-12 shadow-xl">
          <div className="max-w-2xl relative z-10 space-y-4">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-teal-500/20 text-teal-300 border border-teal-500/30">
              <span className="w-2 h-2 rounded-full bg-teal-400 animate-pulse" />
              Connected AI Clinical Triage & Scheduling
            </span>
            <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight leading-tight">
              Compassionate Care Meets <span className="text-teal-400">Intelligent Health</span>
            </h1>
            <p className="text-slate-300 text-sm sm:text-base leading-relaxed">
              Find verified hospital specialists, book appointments with zero wait times, and receive instant,
              grounded clinical guidance powered by our context-aware agentic healthcare chatbot.
            </p>
            <div className="pt-2 flex flex-wrap gap-3">
              <button
                onClick={() => setActiveTab('doctors')}
                className="px-5 py-2.5 rounded-xl bg-teal-500 text-slate-950 font-semibold text-sm hover:bg-teal-400 shadow-md shadow-teal-500/20 transition"
              >
                Find a Specialist
              </button>
              <button
                onClick={() => setActiveTab('triage')}
                className="px-5 py-2.5 rounded-xl bg-white/10 hover:bg-white/15 text-white font-semibold text-sm border border-white/20 backdrop-blur-md transition"
              >
                Start Symptom Triage
              </button>
            </div>
          </div>
        </section>

        {/* Feature Cards Grid */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 bg-white rounded-2xl border border-slate-200/80 shadow-xs hover:border-teal-300 transition">
            <div className="w-10 h-10 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center font-bold text-lg mb-4">
              🩺
            </div>
            <h3 className="text-base font-bold text-slate-900 mb-1">Accredited Specialists</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Board-certified doctors across Cardiology, Neurology, Pediatrics, Dermatology, and Orthopedics.
            </p>
          </div>

          <div className="p-6 bg-white rounded-2xl border border-slate-200/80 shadow-xs hover:border-teal-300 transition">
            <div className="w-10 h-10 rounded-xl bg-cyan-50 text-cyan-600 flex items-center justify-center font-bold text-lg mb-4">
              ⚡
            </div>
            <h3 className="text-base font-bold text-slate-900 mb-1">Emergency-First Triage</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Immediate short-circuit detection for critical symptoms with direct routing to 911 / emergency care.
            </p>
          </div>

          <div className="p-6 bg-white rounded-2xl border border-slate-200/80 shadow-xs hover:border-teal-300 transition">
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold text-lg mb-4">
              🛡️
            </div>
            <h3 className="text-base font-bold text-slate-900 mb-1">Grounded RAG Intelligence</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Zero hallucinations. Every clinical statement is cited from hospital data and verified medical guidelines.
            </p>
          </div>
        </section>

        {/* Specialists Preview */}
        <section className="bg-white rounded-3xl p-8 border border-slate-200/80 shadow-xs space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-slate-900">PulseCare Medical Staff</h2>
              <p className="text-xs text-slate-500 mt-0.5">Explore our on-duty verified specialists</p>
            </div>
            <span className="text-xs text-teal-600 font-semibold bg-teal-50 px-3 py-1 rounded-full border border-teal-200">
              5 Departments Active
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl border border-slate-200 hover:border-teal-300 transition space-y-1.5">
              <span className="text-xs font-semibold text-teal-700 bg-teal-50 px-2 py-0.5 rounded">Cardiology</span>
              <h4 className="text-sm font-bold text-slate-900">Dr. Sarah Smith</h4>
              <p className="text-xs text-slate-500">MD, FACC - Harvard Medical School</p>
              <div className="text-xs text-slate-600 pt-1">
                <strong>Hours:</strong> Mon-Fri 09:00 - 16:00 (Suite 204)
              </div>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 hover:border-teal-300 transition space-y-1.5">
              <span className="text-xs font-semibold text-teal-700 bg-teal-50 px-2 py-0.5 rounded">Neurology</span>
              <h4 className="text-sm font-bold text-slate-900">Dr. David Chen</h4>
              <p className="text-xs text-slate-500">MD, PhD - Johns Hopkins University</p>
              <div className="text-xs text-slate-600 pt-1">
                <strong>Hours:</strong> Mon-Thu 10:00 - 17:00 (Suite 305)
              </div>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 hover:border-teal-300 transition space-y-1.5">
              <span className="text-xs font-semibold text-teal-700 bg-teal-50 px-2 py-0.5 rounded">Pediatrics</span>
              <h4 className="text-sm font-bold text-slate-900">Dr. Priya Patel</h4>
              <p className="text-xs text-slate-500">MBBS, MD - Stanford Health Care</p>
              <div className="text-xs text-slate-600 pt-1">
                <strong>Hours:</strong> Tue-Sat 08:30 - 15:30 (Suite 108)
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="mt-auto border-t border-slate-200 bg-white py-6 text-center text-xs text-slate-500">
        <p>© 2026 PulseCare Healthcare System. All rights reserved. HIPAA Compliant.</p>
        <p className="mt-1 text-[11px] text-slate-400">
          For medical emergencies, please dial 911 or visit your nearest Emergency Department immediately.
        </p>
      </footer>

      {/* Floating Isolated AI Chatbot Widget */}
      <ChatWidget authToken={authToken} />
    </div>
  );
}

import React, { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import {
  AlertCircle,
  Bot,
  Info,
  KeyRound,
  Send,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  User,
} from 'lucide-react';

export default function App() {
  const [apiKey, setApiKey] = useState('');
  const [messages, setMessages] = useState([
    {
      id: '1',
      text: "Hello! I'm your AI Healthcare Assistant. How can I help you today?",
      sender: 'bot',
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const hasApiKey = apiKey.trim().length > 0;

  useEffect(() => {
    const savedKey = localStorage.getItem('gemini_key');
    if (savedKey) setApiKey(savedKey);
  }, []);

  useEffect(() => {
    if (apiKey) {
      localStorage.setItem('gemini_key', apiKey);
    }
  }, [apiKey]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    if (!hasApiKey) {
      alert('Please enter your Gemini API key');
      return;
    }

    const userMessage = {
      id: Date.now().toString(),
      text: input,
      sender: 'user',
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: input,
          api_key: apiKey,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || data.detail || 'Request failed');
      }

      const botMessage = {
        id: (Date.now() + 1).toString(),
        text: data.response,
        sender: 'bot',
        context: data.context,
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error('Chat error:', error);

      let errorMessage = 'Something went wrong. Please try again.';
      if (error instanceof Error && error.message.includes('API key')) {
        errorMessage = 'Invalid Gemini API key. Please check and try again.';
      } else if (error instanceof Error && error.message) {
        errorMessage = error.message;
      }

      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          text: errorMessage,
          sender: 'bot',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top,_rgba(6,182,212,0.18),_transparent_24%),radial-gradient(circle_at_bottom_left,_rgba(34,197,94,0.14),_transparent_26%),linear-gradient(135deg,_#f6fbff_0%,_#f3fbf8_42%,_#f8f4ff_100%)] text-slate-900">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <motion.div
          animate={{ y: [0, -18, 0], x: [0, 10, 0] }}
          transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute left-[-7rem] top-16 h-72 w-72 rounded-full bg-emerald-300/20 blur-3xl"
        />
        <motion.div
          animate={{ y: [0, 20, 0], x: [0, -12, 0] }}
          transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute right-[-6rem] top-24 h-80 w-80 rounded-full bg-cyan-300/20 blur-3xl"
        />
        <motion.div
          animate={{ y: [0, -16, 0] }}
          transition={{ duration: 11, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute bottom-0 left-1/4 h-72 w-72 rounded-full bg-fuchsia-200/20 blur-3xl"
        />
      </div>

      <header className="sticky top-0 z-20 border-b border-white/40 bg-white/60 backdrop-blur-2xl">
        <div className="mx-auto flex h-20 max-w-6xl items-center justify-between px-4">
          <motion.div
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45 }}
            className="flex items-center gap-3"
          >
            <div className="relative flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-500 via-teal-500 to-cyan-500 text-white shadow-[0_16px_40px_rgba(20,184,166,0.32)]">
              <Stethoscope size={24} />
              <div className="absolute -right-1 -top-1 rounded-full bg-white p-1 text-emerald-600">
                <Sparkles size={10} />
              </div>
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-[-0.03em]">HealthAssist AI</h1>
              <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">Modern RAG Healthcare Workspace</p>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.45, delay: 0.08 }}
            className="hidden items-center gap-2 rounded-full border border-white/60 bg-white/70 px-3 py-2 text-xs text-slate-600 shadow-sm md:flex"
          >
            <ShieldCheck size={14} className="text-emerald-600" />
            Private key session
          </motion.div>
        </div>
      </header>

      <main className="relative mx-auto grid min-h-[calc(100vh-5rem)] max-w-6xl gap-6 px-4 py-6 pb-32 lg:grid-cols-[320px_minmax(0,1fr)]">
        <motion.aside
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.45 }}
          className="h-fit rounded-[28px] border border-white/60 bg-white/65 p-5 shadow-[0_24px_70px_rgba(15,23,42,0.08)] backdrop-blur-2xl"
        >
          <div className="mb-6">
            <div className="mb-3 inline-flex rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-[11px] font-medium uppercase tracking-[0.22em] text-emerald-700">
              Secure Access
            </div>
            <h2 className="text-2xl font-semibold tracking-[-0.04em] text-slate-900">Clinical assistant with cleaner motion</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Ask about symptoms, medicines, precautions, and lifestyle guidance. Your Gemini key stays only in this browser session.
            </p>
          </div>

          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200/70 bg-white/80 p-4">
              <div className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-800">
                <KeyRound size={15} className="text-emerald-600" />
                Gemini API Key
              </div>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Enter your Gemini API Key"
                className="w-full rounded-2xl border border-slate-200 bg-slate-50/90 px-4 py-3 text-sm outline-none transition-all placeholder:text-slate-400 focus:border-emerald-400 focus:bg-white focus:ring-4 focus:ring-emerald-500/10"
              />
              <p className="mt-2 text-[11px] leading-5 text-slate-500">
                Your API key is not stored and is used only for this session.
              </p>
            </div>

            <div className="rounded-2xl bg-slate-950 p-4 text-slate-50 shadow-[0_18px_40px_rgba(15,23,42,0.18)]">
              <div className="mb-2 flex items-center gap-2 text-sm font-medium">
                <Sparkles size={15} className="text-emerald-300" />
                What this assistant returns
              </div>
              <div className="flex flex-wrap gap-2 text-[11px] text-slate-300">
                <span className="rounded-full bg-white/10 px-2.5 py-1">Advice</span>
                <span className="rounded-full bg-white/10 px-2.5 py-1">Diet & Lifestyle</span>
                <span className="rounded-full bg-white/10 px-2.5 py-1">Medicine</span>
                <span className="rounded-full bg-white/10 px-2.5 py-1">Doctor Visit</span>
              </div>
            </div>

            <div className="rounded-2xl border border-white/60 bg-gradient-to-br from-white to-sky-50 p-4">
              <div className="mb-1 text-sm font-medium text-slate-800">Session status</div>
              <div className={`inline-flex rounded-full px-3 py-1 text-[11px] font-medium ${
                hasApiKey ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
              }`}>
                {hasApiKey ? 'Ready to chat' : 'Waiting for API key'}
              </div>
            </div>
          </div>
        </motion.aside>

        <motion.section
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.08 }}
          className="flex min-h-[72vh] flex-col rounded-[30px] border border-white/60 bg-white/62 shadow-[0_30px_100px_rgba(15,23,42,0.10)] backdrop-blur-2xl"
        >
          <div className="flex items-center justify-between border-b border-slate-200/70 px-5 py-4">
            <div>
              <div className="text-sm font-semibold text-slate-900">Care conversation</div>
              <div className="text-xs text-slate-500">Structured, retrieval-backed responses</div>
            </div>
            <div className="hidden items-center gap-2 rounded-full border border-slate-200 bg-white/80 px-3 py-1.5 text-xs text-slate-500 sm:flex">
              <Info size={14} />
              Verify medical advice with a professional
            </div>
          </div>

          <div className="flex-1 space-y-6 overflow-y-auto px-5 py-6">
            {messages.length === 1 && !isLoading && (
              <motion.div
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-[28px] border border-dashed border-emerald-200/80 bg-white/55 p-6 text-center shadow-[0_16px_50px_rgba(15,23,42,0.04)]"
              >
                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-500 via-teal-500 to-cyan-500 text-white shadow-[0_18px_40px_rgba(20,184,166,0.28)]">
                  <Stethoscope size={24} />
                </div>
                <h3 className="text-lg font-semibold tracking-[-0.03em] text-slate-900">Start a healthcare conversation</h3>
                <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-600">
                  Ask about symptoms, medicines, precautions, or general health guidance. Retrieved context appears beneath AI answers for transparency.
                </p>
              </motion.div>
            )}

            <AnimatePresence initial={false}>
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 20, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ duration: 0.28, ease: 'easeOut' }}
                  className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`flex max-w-[94%] gap-3 md:max-w-[80%] ${msg.sender === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                    <div className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-2xl shadow-sm ${
                      msg.sender === 'user'
                        ? 'bg-slate-900 text-white'
                        : 'bg-gradient-to-br from-emerald-100 to-cyan-100 text-emerald-700'
                    }`}>
                      {msg.sender === 'user' ? <User size={18} /> : <Bot size={18} />}
                    </div>

                    <div className="space-y-2">
                      <div className={`rounded-[24px] p-4 shadow-sm ${
                        msg.sender === 'user'
                          ? 'rounded-tr-md bg-gradient-to-br from-emerald-500 via-teal-500 to-cyan-500 text-white shadow-[0_20px_40px_rgba(20,184,166,0.28)]'
                          : 'rounded-tl-md border border-white/70 bg-white/88 text-slate-800 shadow-[0_10px_30px_rgba(15,23,42,0.06)]'
                      }`}>
                        <div className={`mb-2 text-[10px] font-medium uppercase tracking-[0.22em] ${
                          msg.sender === 'user' ? 'text-white/75' : 'text-slate-400'
                        }`}>
                          {msg.sender === 'user' ? 'You' : 'HealthAssist AI'}
                        </div>
                        <p className="whitespace-pre-wrap text-sm leading-7">{msg.text}</p>
                      </div>

                      {msg.context && msg.context.length > 0 && (
                        <details className="cursor-pointer rounded-2xl border border-slate-200/80 bg-slate-50/80 p-3 text-[11px] text-slate-500 transition-colors hover:border-emerald-200 hover:text-slate-700">
                          <summary className="list-none flex items-center gap-2 font-medium">
                            <AlertCircle size={12} />
                            View retrieved context ({msg.context.length} sources)
                          </summary>
                          <div className="mt-3 space-y-2">
                            {msg.context.map((ctx, index) => (
                              <div key={index} className="rounded-xl border border-slate-200 bg-white p-3">
                                <p className="font-medium text-slate-700">
                                  Source {index + 1} (Sim: {(ctx.similarity * 100).toFixed(1)}%)
                                </p>
                                <p className="mt-1 italic text-slate-500">"{ctx.text.substring(0, 120)}..."</p>
                              </div>
                            ))}
                          </div>
                        </details>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {isLoading && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex justify-start"
              >
                <div className="flex items-center gap-3 rounded-[24px] rounded-tl-md border border-white/70 bg-white/90 p-4 shadow-[0_12px_30px_rgba(15,23,42,0.06)]">
                  <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-100 to-cyan-100 text-emerald-700">
                    <Bot size={18} />
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="h-2.5 w-2.5 rounded-full bg-emerald-400 animate-bounce" />
                    <div className="h-2.5 w-2.5 rounded-full bg-cyan-400 animate-bounce [animation-delay:0.15s]" />
                    <div className="h-2.5 w-2.5 rounded-full bg-teal-400 animate-bounce [animation-delay:0.3s]" />
                  </div>
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>

          <div className="border-t border-slate-200/70 bg-white/70 px-4 py-4 backdrop-blur-xl">
            <div className="rounded-[28px] border border-white/70 bg-white/85 p-3 shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
              <div className="relative flex items-center gap-2">
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  placeholder="Describe your symptoms or ask about a medicine..."
                  className="w-full rounded-[22px] bg-slate-100/90 px-5 py-4 pr-16 text-sm outline-none transition-all placeholder:text-slate-400 focus:bg-white focus:ring-4 focus:ring-emerald-500/10 disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={!hasApiKey}
                />
                <motion.button
                  whileHover={{ scale: 1.04 }}
                  whileTap={{ scale: 0.96 }}
                  onClick={handleSend}
                  disabled={!hasApiKey || isLoading || !input.trim()}
                  className="absolute right-2 flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-500 via-teal-500 to-cyan-500 text-white shadow-[0_14px_30px_rgba(20,184,166,0.35)] transition-all disabled:cursor-not-allowed disabled:from-slate-300 disabled:via-slate-300 disabled:to-slate-300 disabled:shadow-none"
                >
                  <Send size={18} />
                </motion.button>
              </div>

              <div className="mt-3 flex flex-col gap-2 text-[11px] text-slate-500 md:flex-row md:items-center md:justify-between">
                <p>This is an AI assistant. Always consult a professional for medical advice.</p>
                <p>{hasApiKey ? 'Gemini key connected for this session' : 'Enter a Gemini API key to enable chat'}</p>
              </div>
            </div>
          </div>
        </motion.section>
      </main>
    </div>
  );
}

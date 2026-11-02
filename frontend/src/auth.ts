import { createClient } from '@supabase/supabase-js';
const url=import.meta.env.VITE_SUPABASE_URL;
const key=import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;
if (key && !key.startsWith('sb_publishable_')) throw new Error('O frontend aceita somente uma chave publicável do Supabase');
export const supabase=url&&key?createClient(url,key):null;

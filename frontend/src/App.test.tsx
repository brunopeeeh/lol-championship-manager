import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {describe,it,expect,vi} from 'vitest';
import App from './App';
vi.mock('./auth',()=>({supabase:null}));
const filters={regions:['CBLOL','LCK'],seasons:[2026,2025],teams:[],storage:'supabase'};
const dashboard={players:1,teams:1,matches:20,ratings:1,global_overalls:0,regions:['CBLOL'],distribution:[],attribute_status:{estimated:10,unavailable:2},storage:'supabase',calibration_status:'experimental'};
function server(fail=false){return vi.spyOn(globalThis,'fetch').mockImplementation(async input=>{const url=String(input);if(fail)return {ok:false,status:503,json:async()=>({detail:'Banco indisponível'})} as Response;const data=url.includes('/filters')?filters:url.includes('/dashboard')?dashboard:{items:[{id:'p1',player_id:'p1',name:'Fixture de teste',team:'Equipe de teste',region:'CBLOL',position:'mid',season:2026,overall:null,potential:null,confidence:.2,games:20}],total:1,page:1,page_size:30,storage:'supabase'};return {ok:true,json:async()=>data} as Response})}
describe('scouting conectado',()=>{
 it('distingue reserva noticiada de saída no cadastro',async()=>{
   vi.spyOn(globalThis,'fetch').mockImplementation(async input=>{
     const url=String(input);
     const data=url.includes('/filters')?filters:url.includes('/dashboard')?dashboard:{items:[{
       id:'p',player_id:'p',name:'Keine',team:'paiN Gaming',region:'CBLOL',position:'mid',season:2026,
       overall:null,potential:null,confidence:.2,games:20,
       roster_context:{events:[{kind:'bench_reported',team:'paiN Gaming',reported_date:'2026-08-28'}]}
     }],total:1,page:1,page_size:30};
     return {ok:true,json:async()=>data} as Response;
   });
   render(<App/>);fireEvent.click(screen.getByRole('button',{name:/Jogadores/}));
   expect(await screen.findByText('Reserva noticiada · paiN Gaming: 2026-08-28')).toBeVisible();
   expect(screen.queryByText(/Saída de paiN/)).not.toBeInTheDocument();
 });
 it('apresenta contagens recebidas do backend sem gerar overall ausente',async()=>{server();render(<App/>);expect(await screen.findByText('Jogadores reais')).toBeVisible();expect(screen.getByText('Supabase · PostgreSQL')).toBeVisible();expect(screen.getByText('0 disponíveis')).toBeVisible()});
 it('consulta jogadores com paginação, temporada e região e mantém N/D',async()=>{const fetch=server();render(<App/>);fireEvent.click(screen.getByRole('button',{name:/Jogadores/}));expect(await screen.findByText('Fixture de teste')).toBeVisible();expect(screen.getAllByText('N/D').length).toBeGreaterThanOrEqual(2);fireEvent.change(screen.getByLabelText('Região'),{target:{value:'LCK'}});await waitFor(()=>expect(fetch.mock.calls.some(([url])=>String(url).includes('region=LCK')&&String(url).includes('page=1')&&String(url).includes('page_size=30'))).toBe(true))});
 it('mostra falha externa em vez de dados de sucesso inventados',async()=>{server(true);render(<App/>);expect((await screen.findAllByRole('alert'))[0]).toHaveTextContent('Banco indisponível');expect(screen.queryByText('Jogadores reais')).not.toBeInTheDocument()});
 it('mantém a conta opcional e não envia credenciais se não configurada',async()=>{server();render(<App/>);fireEvent.click(screen.getByRole('button',{name:/Conta/}));expect(await screen.findByText(/Configure as variáveis publicáveis/)).toBeVisible()});
 it('separa elenco anunciado de estatísticas antigas e exibe saída posterior',async()=>{
   const source={url:'https://example.org/source',provider:'Fonte de teste',published_at:'2026-07-24',retrieved_at:'2026-11-01',type:'editorial'};
   const event={name:'ZekaS',team:'VKS',kind:'departure_reported',reported_date:'2026-10-06',effective_date:null,source_ids:['s'],note:'Saída noticiada',confidence:'secondary_report'};
   vi.spyOn(globalThis,'fetch').mockImplementation(async input=>({ok:true,json:async()=>String(input).includes('/filters')?filters:String(input).includes('/dashboard')?dashboard:{reviewed_at:'2026-11-01',warning:'Contratos atuais não verificados',sources:{s:source},snapshots:[{id:'s',competition:'CBLOL 2026 Split 2',reference_date:'2026-07-24',note:'Quinteto anunciado',teams:[{name:'VKS',players:[{name:'ZekaS',position:'top',later_events:[event]}]}]}]}} as Response));
   render(<App/>);fireEvent.click(screen.getByRole('button',{name:/Equipes/}));
   expect(await screen.findByText('ZekaS')).toBeVisible();
   expect(screen.getByText('Saída noticiada: 2026-10-06')).toBeVisible();
   expect(screen.getByText('Contratos atuais não verificados')).toBeVisible();
   expect(screen.queryByText('OVR')).not.toBeInTheDocument();
   expect(screen.getByLabelText('Base do elenco')).toHaveValue('reviewed');
 });
});

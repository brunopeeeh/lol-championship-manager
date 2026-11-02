import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {vi,it,expect} from 'vitest';
import {RosterTimeline,TransferCenter} from './Intelligence';

it('consulta anúncios até a data selecionada e mostra ausência sem inferir elenco',async()=>{
 const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:true,json:async()=>({items:[],competitions:['CBLOL 2026 Split 2'],sources:{},warning:'Histórico editorial'})} as Response);
 render(<RosterTimeline/>);
 expect(await screen.findByText(/Não há registro histórico revisado/)).toBeVisible();
 fireEvent.change(screen.getByLabelText('Data da consulta'),{target:{value:'2026-04-01'}});
 await waitFor(()=>expect(fetch.mock.calls.some(([url])=>String(url).includes('as_of=2026-04-01'))).toBe(true));
});

it('distingue notícias ausentes de ausência de transferências',async()=>{
 vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:true,json:async()=>({items:[],teams:[],sources:{},kinds:{},warning:'Cobertura parcial'})} as Response);
 render(<TransferCenter/>);
 expect(await screen.findByText(/Isso não comprova ausência de transferências/)).toBeVisible();
});

import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { ProfileFormActions } from './ProfileFormActions';
import { profileStatus } from '../editor-utils';

it('has exactly one form submit while saving', () => {
 const submit=vi.fn(e=>e.preventDefault());
 const { rerender }=render(<form onSubmit={submit}><ProfileFormActions model="person" isNew={false} state="saving" dirty disabled={false}/></form>);
 expect(screen.getByRole('button',{name:'Lagre person'})).toBeDisabled();
 expect(screen.queryByRole('button', {name: /profilutkast/})).not.toBeInTheDocument();
 expect(document.querySelectorAll('button[type="submit"]')).toHaveLength(1);
 rerender(<form onSubmit={submit}><ProfileFormActions model="person" isNew={false} state="idle" dirty={true} disabled={false}/></form>);
 fireEvent.click(screen.getByRole('button',{name:'Lagre person'}));
 expect(submit).toHaveBeenCalledTimes(1);
 expect(screen.getByRole('status')).toHaveTextContent('Ulagrede profilfelt');
 expect(screen.queryByText(/Sist lagret/)).not.toBeInTheDocument();
});
it('prioritizes active request/error, then new edits over old saved',()=>{
 expect(profileStatus('saving',true,false,'person').label).toMatch(/Lagrer/);
 expect(profileStatus('error',true,false,'person').label).toBe('Lagring ikke bekreftet');
 expect(profileStatus('saved',true,false,'person').label).toBe('Ulagrede profilfelt');
 expect(profileStatus('saved',false,false,'person').label).toBe('Personskjema lagret');
 expect(profileStatus('idle',false,true,'person').label).toBe('Nytt profilutkast');
});


it('keeps a clean profile quiet and disables redundant writes', () => {
 render(<form><ProfileFormActions model="aktør" isNew={false} state="idle" dirty={false} disabled={false}/></form>);
 expect(screen.getByRole('status')).toBeEmptyDOMElement();
 expect(screen.getByRole('button',{name:'Lagre aktør'})).toBeDisabled();
 expect(screen.queryByRole('button', {name: /profilutkast/})).not.toBeInTheDocument();
});

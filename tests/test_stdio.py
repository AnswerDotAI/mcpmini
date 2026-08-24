import asyncio
from types import SimpleNamespace

from mcpmini.core import MCPServer, StdioTransport, jtool, stdio_peer


async def _nested_stdio_requests_fail_and_recover():
    async def full_name():
        "Collect a full name interactively."
        first = await srv.elicit('First name', dict(type='object'))
        last = await srv.elicit('Last name', dict(type='object'))
        return f"{first['content']['value']} {last['content']['value']}"

    srv = MCPServer('interactive', [full_name])
    prompts,answers = [],iter(('Ada', 'Lovelace'))
    async def answer(method, params):
        prompts.append((method, params['message']))
        return dict(action='accept', content=dict(value=next(answers)))

    async with stdio_peer(srv) as peer:
        tr = StdioTransport([], on_request=answer)
        tr.p = SimpleNamespace(stdin=peer.writer, stdout=peer.reader)
        res = await tr.send(jtool('full_name'))
        assert res['result']['content'][0]['text'] == 'Ada Lovelace'
        assert prompts == [('elicitation/create', 'First name'), ('elicitation/create', 'Last name')]

        def refuse(method, params): raise ValueError('input refused')
        tr.on_request = refuse
        failed = (await tr.send(jtool('full_name', 2)))['result']
        assert failed['isError'] and 'input refused' in failed['content'][0]['text']

        answers = iter(('Grace', 'Hopper'))
        tr.on_request = answer
        recovered = await tr.send(jtool('full_name', 3))
        assert recovered['result']['content'][0]['text'] == 'Grace Hopper'


def test_nested_stdio_requests_fail_and_recover(): asyncio.run(_nested_stdio_requests_fail_and_recover())

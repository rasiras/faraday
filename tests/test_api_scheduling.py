"""
Faraday Penetration Test IDE
Copyright (C) 2019  Infobyte LLC (http://www.infobytesec.com/)
See the file 'doc/LICENSE' for the license information

"""
from dataclasses import dataclass
from unittest import mock

import pytest

from faraday.server.api.modules.agents_schedule import AgentsScheduleView
from faraday.server.models import AgentsSchedule
from tests.test_api_non_workspaced_base import ReadWriteAPITests
from tests.factories import (
    AgentScheduleFactory,
    AgentFactory,
    WorkspaceFactory,
    ExecutorFactory,
    AgentExecutionFactory
)


def test_both_schedule_and_manual_agents(session):
    workspace = WorkspaceFactory.create()
    agent = AgentFactory.create()
    executor = ExecutorFactory.create(agent=agent)
    schedule = AgentScheduleFactory.create(crontab='*/5 * * * *', workspaces=[workspace], executor=executor)

    agents = (agent, schedule)
    agents_execution = [AgentExecutionFactory.create(executor=executor, workspace=workspace) for _ in agents]

    keys = ['executor', 'workspace', 'parameters_data']
    for key in keys:
        assert getattr(agents_execution[0], key) == getattr(agents_execution[1], key)
    assert getattr(agents_execution[0], 'command') != getattr(agents_execution[1], 'command')


@dataclass
class LicenseTest:
    agent_scheduler_limit: int = 99


class TestAgentScheduleView(ReadWriteAPITests):
    model = AgentsSchedule
    factory = AgentScheduleFactory
    api_endpoint = 'agents_schedule'
    view_class = AgentsScheduleView
    patchable_fields = ["description"]

    @pytest.mark.parametrize("method", ["PUT", "PATCH"])
    def test_update_an_object(self, test_client, user, session, method):
        super().test_update_an_object(test_client, user, method)

    def test_retrieve_one_object(self, test_client, user, session):
        super().test_retrieve_one_object(test_client, user)

    def test_delete_scheduling_when_deleting_agent(self, test_client, session, user):
        workspaces = [WorkspaceFactory.create()]
        agent = AgentFactory.create()
        session.add(agent)

        executor = ExecutorFactory.create(agent=agent)
        session.add(executor)

        agent_schedule = AgentScheduleFactory.create(crontab='*/5 * * * *',
                                                    workspaces=workspaces,
                                                    executor=executor)
        session.add(agent_schedule)

        session.commit()

        delete_agent_res = test_client.delete(f'/v3/agents/{agent.id}')

        assert delete_agent_res.status_code == 204

        find_agent_schedule_res = test_client.get(self.url(agent_schedule))

        assert find_agent_schedule_res.status_code == 404

    def test_create_valid_cron(self, test_client, session, user):
        workspaces = [WorkspaceFactory.create()]
        agent = AgentFactory.create()
        executor = ExecutorFactory.create(agent=agent)
        session.commit()
        agent_schedule = AgentScheduleFactory.build_dict(workspace=workspaces,
                                                         executor=executor)
        agent_schedule['crontab'] = '*/5 * * * *'
        res = test_client.post(self.url(), data=agent_schedule)
        assert res.status_code == 201

    def test_create_invalid_cron(self, test_client, session, user):
        workspaces = [WorkspaceFactory.create()]
        agent = AgentFactory.create()
        executor = ExecutorFactory.create(agent=agent)
        session.commit()
        agent_schedule = AgentScheduleFactory.build_dict(workspace=workspaces,
                                                         executor=executor)
        agent_schedule['crontab'] = 'daily'
        res = test_client.post(self.url(), data=agent_schedule)
        assert res.status_code == 400

    def test_create_valid_complex_cron(self, test_client, session, user):
        workspaces = [WorkspaceFactory.create()]
        agent = AgentFactory.create()
        executor = ExecutorFactory.create(agent=agent)
        session.commit()
        agent_schedule = AgentScheduleFactory.build_dict(workspace=workspaces,
                                                         executor=executor)
        agent_schedule['crontab'] = '30-42/2,20-30 18-20/92 11-21/39 2-12/8 3-4/1,4'
        res = test_client.post(self.url(), data=agent_schedule)
        assert res.status_code == 201

    def test_create_until_limit(self, test_client, session):
        with mock.patch('faraday.server.api.modules.agents_schedule.SCHEDULES_LIMIT', 7):
            for i in range(2):
                workspaces = [WorkspaceFactory.create()]
                agent = AgentFactory.create()
                executor = ExecutorFactory.create(agent=agent)
                session.commit()
                agent_schedule = AgentScheduleFactory.build_dict(workspace=workspaces,
                                                                 executor=executor)
                res = test_client.post(self.url(), data=agent_schedule)
                assert res.status_code == 201
            # Agent schedules 7 - limit 7
            workspaces = [WorkspaceFactory.create()]
            agent = AgentFactory.create()
            executor = ExecutorFactory.create(agent=agent)
            session.commit()
            agent_schedule = AgentScheduleFactory.build_dict(workspace=workspaces,
                                                             executor=executor)
            res = test_client.post(self.url(), data=agent_schedule)
            assert res.status_code == 403

    def test_patch_update_an_object_does_not_fail_with_partial_data(self, test_client, logged_user):
        super().test_patch_update_an_object_does_not_fail_with_partial_data(test_client, logged_user)

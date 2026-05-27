import {
  App,
  Col,
  Flex,
  Row,
  Tabs,
  TabsProps,
  Tooltip,
  Typography,
} from 'antd';
const { Title, Text } = Typography;
import { FC, useMemo, useRef, useState } from 'react';
import Cookies from 'js-cookie';
import { SyncOutlined } from '@ant-design/icons';

import { BETA_REPORTS_MENU_ITEMS } from '@/constants/menu.constants';
import { APP_ENV } from '@shared/ui/constants/env.constants';
import customDayjs from '@shared/ui/libs/dayjs.libs';
import { DEFAULT_DATE_FORMAT } from '@shared/ui/constants/common.constants';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';

import { StyledBetaReportsContainer } from '@/components/templates/BetaReportsTemplate/BetaReportsTemplate.styled';
import AppsContainer from '@shared/ui/components/containers/AppsContainer';
import Reports from '@/components/organisms/Reports';
import ActiveIssues from '@/components/organisms/ActiveIssues';
import CustomRangePicker from '@shared/ui/components/atoms/DatePickers/CustomRangePicker';
import DeviceSelect from '@/components/molecules/Selects/DeviceSelect';
import PlatformSelect from '@/components/molecules/Selects/PlatformSelect';
import ReleaseSelect from '@/components/molecules/Selects/ReleaseSelect';
import PrioritySelect from '@/components/molecules/Selects/PrioritySelect';
import IconButton from '@shared/ui/components/atoms/Buttons/IconButton';
import ReportsChat from '@/components/organisms/ReportsChat';
import ReportsAccessBlock from '@/components/organisms/ReportsAccessBlock';

import { BetaReportsTemplateProps } from '@/components/templates/BetaReportsTemplate/BetaReportsTemplate.props';
import { PlatformEnum } from '@/enums/beta-reports.enum';
import { ReportsRef } from '@/components/organisms/Reports/Reports.props';
import { ActiveIssuesRef } from '@/components/organisms/ActiveIssues/ActiveIssues.props';
import { ReportsChatRef } from '@/components/organisms/ReportsChat/ReportsChat.props';

const BetaReportsTemplate: FC<BetaReportsTemplateProps> = ({
  availableDevicesOptions = [],
  availablePlatformsOptions = [],
  activeChat,
  defaultDevice,
  defaultRelease,
  defaultPriority,
  defaultPlatform = PlatformEnum.ATV,
  defaultDateRange = [],
  hasAccess = false,
}) => {
  const { message } = App.useApp();
  const handleError = useHandleError();
  const [dateRange, setDateRange] = useState<any>(
    defaultDateRange?.length
      ? [
          customDayjs(defaultDateRange[0], DEFAULT_DATE_FORMAT),
          customDayjs(defaultDateRange[1], DEFAULT_DATE_FORMAT),
        ]
      : null,
  );
  const [platform, setPlatform] = useState<string>(defaultPlatform);
  const [release, setRelease] = useState<number | undefined>(
    defaultRelease ? +defaultRelease : undefined,
  );
  const userSelectedReleases = useRef<Record<string, number>>({});
  const [device, setDevice] = useState<string | undefined>(defaultDevice);
  const [priority, setPriority] = useState<number | undefined>(
    defaultPriority ? +(defaultPriority as string) : undefined,
  );
  const [refetchLoading, setRefetchLoading] = useState(false);
  const reportsRef = useRef<ReportsRef>(null);
  const activeIssuesRef = useRef<ActiveIssuesRef>(null);
  const reportsChatRef = useRef<ReportsChatRef>(null);

  const tabs: TabsProps['items'] = useMemo(
    () => [
      {
        key: '1',
        label: 'Active Issue Candidates',
        children: (
          <Row gutter={5}>
            <Col span={14}>
              {activeChat ? (
                <ReportsChat
                  componentRef={reportsChatRef}
                  chat={activeChat}
                  platform={platform}
                />
              ) : null}
            </Col>
            <Col span={10}>
              <ActiveIssues
                componentRef={activeIssuesRef}
                start_date={dateRange?.[0]}
                end_date={dateRange?.[1]}
                platform={platform}
                release={release}
                min_priority={priority}
              />
            </Col>
          </Row>
        ),
      },
      {
        key: '2',
        label: 'Reports',
        children: (
          <Reports
            componentRef={reportsRef}
            start_date={dateRange?.[0]}
            end_date={dateRange?.[1]}
            platform={platform}
            release={release}
            device={device}
          />
        ),
      },
    ],
    [dateRange, platform, release, device, priority, activeChat],
  );
  const refetchData = async () => {
    try {
      setRefetchLoading(true);
      await Promise.all([
        reportsChatRef?.current?.refetchData(),
        reportsRef?.current?.refetchData(),
        activeIssuesRef?.current?.refetchData(),
      ]);
      message.success('The data has successfully fetched');
    } catch (e) {
      handleError(e);
    } finally {
      setRefetchLoading(false);
    }
  };
  return (
    <AppsContainer menuItems={BETA_REPORTS_MENU_ITEMS}>
      {!hasAccess ? (
        <ReportsAccessBlock />
      ) : (
        <StyledBetaReportsContainer>
          <Flex align='center' justify='space-between' gap={15}>
            <Title>Beta Reports Analysis</Title>
            <Flex align='center' justify='flex-end' gap={10}>
              <Tooltip title='Refetch data'>
                <IconButton
                  type='primary'
                  icon={<SyncOutlined />}
                  onClick={refetchData}
                  loading={refetchLoading}
                />
              </Tooltip>
            </Flex>
          </Flex>

          <Flex align='center' gap={10} wrap>
            <Text strong>Filters: </Text>
            <CustomRangePicker
              value={dateRange}
              onChange={(dates) => {
                setDateRange(dates);
                if (dates && dates?.length > 1) {
                  Cookies.set(
                    'dateRange',
                    JSON.stringify([
                      customDayjs(dates[0]).format(DEFAULT_DATE_FORMAT),
                      customDayjs(dates[1]).format(DEFAULT_DATE_FORMAT),
                    ]),
                    {
                      path: '/',
                      secure: APP_ENV !== 'local',
                      sameSite: 'lax',
                    },
                  );
                } else {
                  Cookies.remove('dateRange');
                }
              }}
            />
            <PlatformSelect
              value={platform}
              onChange={(value) => {
                setPlatform(value);
                // Restore release for this platform if user has selected one before
                setRelease(userSelectedReleases.current[value]);
                if (value) {
                  Cookies.set('platform', value, {
                    path: '/',
                    secure: APP_ENV !== 'local',
                    sameSite: 'lax',
                  });
                } else {
                  Cookies.remove('platform');
                }
              }}
              options={availablePlatformsOptions}
            />
            <ReleaseSelect
              value={release}
              platform={platform}
              onOptionsLoaded={(firstValue) => {
                if (!userSelectedReleases.current[platform] && !release) {
                  setRelease(firstValue);
                }
              }}
              onChange={(value) => {
                setRelease(value);
                if (value) {
                  userSelectedReleases.current[platform] = value;
                  Cookies.set('release', value, {
                    path: '/',
                    secure: APP_ENV !== 'local',
                    sameSite: 'lax',
                  });
                } else {
                  delete userSelectedReleases.current[platform];
                  Cookies.remove('release');
                }
              }}
            />
            <DeviceSelect
              value={device}
              onChange={(value) => {
                setDevice(value);
                if (value) {
                  Cookies.set('device', value, {
                    path: '/',
                    secure: APP_ENV !== 'local',
                    sameSite: 'lax',
                  });
                } else {
                  Cookies.remove('device');
                }
              }}
              options={availableDevicesOptions}
            />
            <PrioritySelect
              value={priority}
              placeholder='Select priority'
              onChange={(value) => {
                setPriority(value);
                if (value) {
                  Cookies.set('priority', value, {
                    path: '/',
                    secure: APP_ENV !== 'local',
                    sameSite: 'lax',
                  });
                } else {
                  Cookies.remove('priority');
                }
              }}
            />
          </Flex>
          <Tabs defaultActiveKey='1' items={tabs} />
        </StyledBetaReportsContainer>
      )}
    </AppsContainer>
  );
};

export default BetaReportsTemplate;

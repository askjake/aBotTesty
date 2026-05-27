import { useMemo, useState } from 'react';
import { SearchOutlined } from '@ant-design/icons';
import { Space, Typography } from 'antd';
const { Title } = Typography;

import { APPS_NAVIGATION } from '@/constants/apps.constants';

import {
  StyledAppsContainer,
  StyledAppsInput,
  StyledAppsWrapper,
} from '@/components/templates/AppsTemplate/AppsTemplate.styled';
import AppsGroup from '@/components/organisms/Apps/AppsGroup';
import ContainerWithSidebar from '@/components/containers/ContainerWithSidebar';

const AppsTemplate = () => {
  const [searchText, setSearchText] = useState<string>('');
  const filteredApps = useMemo(
    () =>
      APPS_NAVIGATION.map((item) => ({
        ...item,
        apps: item.apps.filter((item) =>
          item.name.toLowerCase().includes(searchText.toLowerCase()),
        ),
      })),
    [searchText],
  );
  return (
    <ContainerWithSidebar>
      <StyledAppsContainer variant='borderless'>
        <Title>Applications</Title>
        <StyledAppsInput
          placeholder='Search app by name'
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          prefix={<SearchOutlined />}
        />

        <StyledAppsWrapper>
          {filteredApps.map(({ name, apps = [] }) => (
            <AppsGroup key={name} items={apps} title={name} />
          ))}
        </StyledAppsWrapper>
      </StyledAppsContainer>
    </ContainerWithSidebar>
  );
};

export default AppsTemplate;

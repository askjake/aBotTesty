import { Typography } from 'antd';
const { Title } = Typography;

import { useAppSelector } from '@shared/ui/store';

import ContainerWithSidebar from '@/components/containers/ContainerWithSidebar';
import UpdateVaultForm from '@/components/organisms/VaultMode/UpdateVaultForm';
import SetupVaultForm from '@/components/organisms/VaultMode/SetupVaultForm';
import { StyledVaultModeContainer } from '@/components/templates/VaultModeTemplate/VaultModeTemplate.styled';
import FAQVaultBlock from '@/components/organisms/VaultMode/FAQVaultBlock';

const VaultModeTemplate = () => {
  const vaultModeRegistered = useAppSelector(
    (store) => store.chats.vaultModeRegistered,
  );

  return (
    <ContainerWithSidebar>
      <StyledVaultModeContainer variant='borderless'>
        <Title level={2}>Vault Mode settings</Title>
        <FAQVaultBlock />
        {vaultModeRegistered ? <UpdateVaultForm /> : <SetupVaultForm />}
      </StyledVaultModeContainer>
    </ContainerWithSidebar>
  );
};

export default VaultModeTemplate;

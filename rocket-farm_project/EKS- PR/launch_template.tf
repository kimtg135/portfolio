# EKS node 그룹에서 사용할 시작 템플릿 -> 각 노드별 설정이 필요한 경우 사용되며 taint,laber 설정으로 pod 격리 필요시 사용

resource "aws_launch_template" "eks_node_launch_template" {
  name_prefix = "${var.project_name}-${var.region_name}-eks-node-launch-template-"

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size           = var.eks_launch_template_ebs_management.volume_size
      volume_type           = var.eks_launch_template_ebs_management.volume_type
      encrypted             = var.eks_launch_template_ebs_management.encrypted
      kms_key_id            = aws_kms_key.eks.arn
      delete_on_termination = var.eks_launch_template_ebs_management.delete_on_termination
    }
  }

  network_interfaces {
    security_groups = [
      aws_eks_cluster.this.vpc_config[0].cluster_security_group_id,
      aws_security_group.eks_node_sg.id,
      aws_security_group.eks_cluster_sg.id
    ]
    delete_on_termination = true # 인스턴스 종료 시 네트워크 인터페이스도 삭제
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }
  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "${var.project_name}-${var.region_name}-eks-node"
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}
